from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from multimethod import multimeta
from rich import print as rprint

from model import *


# ===================================================
# IR model
# ===================================================

Instruction = tuple


class Visitor(metaclass=multimeta):
    """
    Clase base Visitor.
    """
    pass


@dataclass
class Storage:
    """
    Describe dónde vive un símbolo en el IR.
    """
    name: str
    ty: Type
    is_global: bool = False
    is_param: bool = False
    is_const: bool = False


@dataclass
class IRFunction:
    name: str
    params: list[tuple[str, Type]]
    return_type: Type
    instructions: list[Instruction] = field(default_factory=list)


@dataclass
class IRProgram:
    globals: list[Instruction] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)

    def format(self) -> str:
        out: list[str] = []

        if self.globals:
            out.append("# Globals")

            for inst in self.globals:
                out.append(format_instruction(inst))

            out.append("")

        for fn in self.functions:
            params = ", ".join(
                f"{name}:{ty}" for name, ty in fn.params
            )

            out.append(
                f"function {fn.name}({params}) -> {fn.return_type}"
            )

            for inst in fn.instructions:
                out.append(f"  {format_instruction(inst)}")

            out.append("")

        return "\n".join(out).rstrip()


# ===================================================
# Pretty printer
# ===================================================

def format_instruction(inst: Instruction) -> str:
    op = inst[0]

    if len(inst) == 1:
        return op

    args = ", ".join(str(x) for x in inst[1:])
    return f"{op} {args}"


# ===================================================
# IR Generator
# ===================================================

class IRCodeGen(Visitor):

    def __init__(self):
        self.program = IRProgram()

        self.current_function: Optional[IRFunction] = None
        self.current_return_type: Type = VoidType

        self.temp_count = 0
        self.label_count = 0

        self.scopes: list[dict[str, Storage]] = []

    # -------------------------------------------------
    # entrypoint
    # -------------------------------------------------

    @classmethod
    def generate(cls, node: Program) -> IRProgram:
        gen = cls()
        gen.visit(node)
        return gen.program

    # -------------------------------------------------
    # helpers
    # -------------------------------------------------

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"R{self.temp_count}"

    def new_label(self, prefix="L") -> str:
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def emit(self, *inst):
        inst = tuple(inst)

        if self.current_function is None:
            self.program.globals.append(inst)
        else:
            self.current_function.instructions.append(inst)

    # -------------------------------------------------
    # scopes
    # -------------------------------------------------

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def bind(self, storage: Storage):
        if not self.scopes:
            self.push_scope()

        self.scopes[-1][storage.name] = storage

    def lookup(self, name: str) -> Storage:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        raise NameError(f"Nombre no definido: {name}")

    # -------------------------------------------------
    # tipos
    # -------------------------------------------------

    def infer_type(self, node: Optional[Node]) -> Type:

        if node is None:
            return VoidType

        ty = getattr(node, "type", None)

        if isinstance(ty, Type):
            return ty

        if isinstance(node, Number):
            return IntegerType

        if isinstance(node, Boolean):
            return BooleanType

        if isinstance(node, Char):
            return CharType

        if isinstance(node, String):
            return StringType

        if isinstance(node, (VarDecl, Param)):
            return node.type

        return IntegerType

    # -------------------------------------------------
    # opcodes
    # -------------------------------------------------

    def type_suffix(self, ty: Type) -> str:

        if ty in (IntegerType, BooleanType):
            return "I"

        if ty == CharType:
            return "B"

        if ty == VoidType:
            return "V"
        
        # 🔥 arrays
        if isinstance(ty, ArrayType):

            # array of integer
            if ty.base == IntegerType:
                return "AI"

            # array of char
            if ty.base == CharType:
                return "AB"

        raise NotImplementedError(f"Tipo no soportado: {ty}")

    def load_opcode(self, ty: Type):
        return f"LOAD{self.type_suffix(ty)}"

    def store_opcode(self, ty: Type):
        return f"STORE{self.type_suffix(ty)}"

    def alloc_opcode(self, ty: Type):
        return f"ALLOC{self.type_suffix(ty)}"

    def var_opcode(self, ty: Type):
        return f"VAR{self.type_suffix(ty)}"

    def print_opcode(self, ty: Type):
        return f"PRINT{self.type_suffix(ty)}"

    # -------------------------------------------------
    # arithmetic
    # -------------------------------------------------

    def binary_arith_opcode(self, oper: str, ty: Type):

        suffix = self.type_suffix(ty)

        table = {
            "+": f"ADD{suffix}",
            "-": f"SUB{suffix}",
            "*": f"MUL{suffix}",
            "/": f"DIV{suffix}",
        }

        if oper not in table:
            raise NotImplementedError(
                f"Operador no soportado: {oper}"
            )

        return table[oper]

    # =================================================
    # PROGRAM
    # =================================================

    def visit(self, node: Program):

        self.push_scope()

        # Primera pasada
        for decl in node.declarations:

            if isinstance(decl, VarDecl):

                self.bind(
                    Storage(
                        decl.name,
                        decl.type,
                        is_global=True,
                    )
                )

            elif isinstance(decl, Function):

                self.bind(
                    Storage(
                        decl.name,
                        FunctionType(
                            decl.return_type,
                            [p.type for p in decl.params]
                        ),
                        is_global=True,
                    )
                )

        # Segunda pasada
        for decl in node.declarations:
            self.visit(decl)

        self.pop_scope()

        return self.program

    # =================================================
    # DECLARATIONS
    # =================================================

    def visit(self, node: VarDecl):

        if self.current_function is None:

            self.emit(
                self.var_opcode(node.type),
                node.name
            )

            if node.value is not None:

                src = self.visit(node.value)

                self.emit(
                    self.store_opcode(node.type),
                    src,
                    node.name
                )

            return

        self.bind(
            Storage(
                node.name,
                node.type,
            )
        )

        self.emit(
            self.alloc_opcode(node.type),
            node.name
        )

        if node.value is not None:

            src = self.visit(node.value)

            self.emit(
                self.store_opcode(node.type),
                src,
                node.name
            )

    def visit(self, node: Function):

        prev_fn = self.current_function
        prev_ret = self.current_return_type

        fn = IRFunction(
            name=node.name,
            params=[(p.name, p.type) for p in node.params],
            return_type=node.return_type,
        )

        self.program.functions.append(fn)

        self.current_function = fn
        self.current_return_type = node.return_type

        self.push_scope()

        # parámetros
        for p in node.params:

            self.bind(
                Storage(
                    p.name,
                    p.type,
                    is_param=True
                )
            )

            self.emit(
                self.alloc_opcode(p.type),
                p.name
            )

        # cuerpo
        if isinstance(node.body, Block):
            self.visit(node.body)

        elif isinstance(node.body, list):
            for stmt in node.body:
                self.visit(stmt)

        # return void automático
        if node.return_type == VoidType:

            if (
                not fn.instructions
                or fn.instructions[-1][0] != "RET"
            ):
                self.emit("RET")

        self.pop_scope()

        self.current_function = prev_fn
        self.current_return_type = prev_ret

    # =================================================
    # BLOCK
    # =================================================

    def visit(self, node: Block):

        self.push_scope()

        for stmt in node.statements:
            self.visit(stmt)

        self.pop_scope()

    # =================================================
    # STATEMENTS
    # =================================================

    def visit(self, node: Assignment):

        if not isinstance(node.target, Identifier):

            raise NotImplementedError(
                "Assignment solo soporta Identifier"
            )

        storage = self.lookup(node.target.name)

        src = self.visit(node.value)

        self.emit(
            self.store_opcode(storage.ty),
            src,
            storage.name
        )

    def visit(self, node: Print):

        for expr in node.args:

            reg = self.visit(expr)

            ty = self.infer_type(expr)

            self.emit(
                self.print_opcode(ty),
                reg
            )

    def visit(self, node: Return):

        if node.value is None:
            self.emit("RET")
            return

        reg = self.visit(node.value)

        self.emit("RET", reg)

    def visit(self, node: If):
        raise NotImplementedError("If no implementado")

    def visit(self, node: While):
        raise NotImplementedError("While no implementado")

    def visit(self, node: For):
        raise NotImplementedError("For no implementado")

    # =================================================
    # EXPRESSIONS
    # =================================================

    def visit(self, node: Identifier):

        storage = self.lookup(node.name)

        tmp = self.new_temp()

        self.emit(
            self.load_opcode(storage.ty),
            storage.name,
            tmp
        )

        return tmp

    def visit(self, node: BinaryOp):

        left_reg = self.visit(node.left)
        right_reg = self.visit(node.right)

        left_ty = self.infer_type(node.left)

        out = self.new_temp()

        if node.op in {"+", "-", "*", "/"}:

            opcode = self.binary_arith_opcode(
                node.op,
                left_ty
            )

            self.emit(
                opcode,
                left_reg,
                right_reg,
                out
            )

            return out

        raise NotImplementedError(
            f"Operador no implementado: {node.op}"
        )

    def visit(self, node: UnaryOp):
        raise NotImplementedError("UnaryOp no implementado")

    def visit(self, node: Call):

        # Evaluar argumentos
        arg_regs = []

        for arg in node.args:
            reg = self.visit(arg)
            arg_regs.append(reg)

        # Temporal para valor retorno
        result = self.new_temp()

        # Generar instrucción CALL
        self.emit("CALL", node.name, *arg_regs, result)

        return result

    def visit(self, node: ArrayAccess):

        # Obtener nombre del arreglo
        if not isinstance(node.array, Identifier):
            raise NotImplementedError(
                "Solo arrays simples soportados"
            )

        storage = self.lookup(node.array.name)

        # Evaluar índice
        index_reg = self.visit(node.index)

        # Registro destino
        out = self.new_temp()

        # LOADARRAY
        self.emit(
            "LOADARRAY",
            storage.name,
            index_reg,
            out
        )

        return out
    # =================================================
    # LITERALS
    # =================================================

    def visit(self, node: Number):

        tmp = self.new_temp()

        self.emit(
            "MOVI",
            int(node.value),
            tmp
        )

        return tmp

    def visit(self, node: Boolean):

        tmp = self.new_temp()

        self.emit(
            "MOVI",
            1 if node.value else 0,
            tmp
        )

        return tmp

    def visit(self, node: Char):

        tmp = self.new_temp()

        value = (
            ord(node.value)
            if isinstance(node.value, str)
            else int(node.value)
        )

        self.emit(
            "MOVB",
            value,
            tmp
        )

        return tmp

    def visit(self, node: String):
        raise NotImplementedError(
            "Strings no implementados"
        )


# ===================================================
# demo
# ===================================================

if __name__ == "__main__":

    ast = Program([
        Function(
            name="main",
            return_type=VoidType,
            params=[],
            body=[
                VarDecl(
                    "x",
                    IntegerType,
                    BinaryOp(
                        "+",
                        Number(2),
                        BinaryOp(
                            "*",
                            Number(3),
                            Number(4)
                        )
                    )
                ),

                Print([
                    Identifier("x")
                ])
            ]
        )
    ])

    ir = IRCodeGen.generate(ast)

    rprint(ir.format())

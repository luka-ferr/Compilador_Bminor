from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from rich import print
import multimethod
from multimethod import multimeta

from model import *


class Visitor(metaclass=multimeta):
    """
    Clase base Visitor.
    """
    pass

# ===================================================
# IR model
# ===================================================

Instruction = tuple


@dataclass
class Storage:
    """
    Describe dónde vive un símbolo durante la generación de IR.

    El objetivo es que el estudiante tenga una estructura simple para
    consultar tipo y categoría del símbolo (global, parámetro, constante).
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
            params = ", ".join(f"{name}:{ty}" for name, ty in fn.params)
            out.append(f"function {fn.name}({params}) -> {fn.return_type}")
            for inst in fn.instructions:
                out.append(f"  {format_instruction(inst)}")
            out.append("")
        return "\n".join(out).rstrip()


# ===================================================
# Pretty printing
# ===================================================


def format_instruction(inst: Instruction) -> str:
    op = inst[0]
    if len(inst) == 1:
        return op
    args = ", ".join(
        repr(x) if isinstance(x, str) and x.startswith("L") else str(x)
        for x in inst[1:]
    )
    return f"{op} {args}"


# ===================================================
# Generator
# ===================================================


class IRCodeGen(Visitor):
    """
    Plantilla base para el proyecto de IRCode.

    Esta versión deja aproximadamente la mitad del trabajo resuelto:

    Ya implementado:
    - estructura del programa IR
    - manejo de temporales y labels
    - scopes y lookup de símbolos
    - declaración de variables y constantes
    - carga de literales enteros, booleanos y chars
    - lectura de variables (VarLoc)
    - impresión simple
    - retorno simple
    - parte de la selección de opcodes

    Pendiente para estudiantes:
    - completar BinOp
    - completar UnaryOp
    - completar Assignment compuesto
    - completar IfStmt / WhileStmt / ForStmt
    - completar FuncCall
    - arreglos y strings
    - conversiones adicionales y mejoras del IR

    Sugerencia pedagógica:
    1. Hacer primero expresiones aritméticas.
    2. Luego comparaciones.
    3. Después control de flujo.
    4. Finalmente llamadas, arreglos y extensiones.
    """

    def __init__(self):
        self.program = IRProgram()
        self.current_function: Optional[IRFunction] = None
        self.current_return_type: Type = VoidType
        self.temp_count = 0
        self.label_count = 0
        self.scopes: list[dict[str, Storage]] = []

    @classmethod
    def generate(cls, node: Program) -> IRProgram:
        gen = cls()
        gen.visit(node)
        return gen.program

    # -------------------------------------------------
    # helpers básicos
    # -------------------------------------------------

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"R{self.temp_count}"

    def new_label(self, prefix: str = "L") -> str:
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def emit(self, *inst) -> None:
        inst = tuple(inst)
        if self.current_function is None:
            self.program.globals.append(inst)
        else:
            self.current_function.instructions.append(inst)

    def push_scope(self) -> None:
        self.scopes.append({})

    def pop_scope(self) -> None:
        self.scopes.pop()

    def bind(self, storage: Storage) -> None:
        if not self.scopes:
            self.push_scope()
        self.scopes[-1][storage.name] = storage

    def lookup(self, name: str) -> Storage:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Nombre no resuelto en IRCodeGen: {name}")

    def infer_type(self, node: Optional[Node]) -> Type:
        """
        Inferencia mínima para que el generador pueda escoger opcodes.

        Nota: aquí se asume que el checker semántico ya pasó antes.
        """
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

        # Valor por defecto conservador para no bloquear pruebas tempranas.
        return IntegerType

    def type_suffix(self, ty: Type) -> str:
        if ty in (IntegerType, BooleanType):
            return "I"
        if ty == CharType:
            return "B"
        if ty == VoidType:
            return "V"
        if ty == FloatType:
            return "F"
        if ty == StringType:
            return "S"
        if isinstance(ty, ArrayType):
            return "A"
        raise NotImplementedError(f"Tipo aún no soportado en esta plantilla: {ty}")

    def move_opcode(self, ty: Type) -> str:
        return f"MOV{self.type_suffix(ty)}"

    def load_opcode(self, ty: Type) -> str:
        return f"LOAD{self.type_suffix(ty)}"

    def store_opcode(self, ty: Type) -> str:
        return f"STORE{self.type_suffix(ty)}"

    def alloc_opcode(self, ty: Type) -> str:
        return f"ALLOC{self.type_suffix(ty)}"

    def var_opcode(self, ty: Type) -> str:
        return f"VAR{self.type_suffix(ty)}"

    def print_opcode(self, ty: Type) -> str:
        return f"PRINT{self.type_suffix(ty)}"

    def cmp_opcode(self, ty: Type) -> str:
        return f"CMP{self.type_suffix(ty)}"

    # -------------------------------------------------
    # opcodes auxiliares
    # -------------------------------------------------

    def binary_arith_opcode(self, oper: str, ty: Type) -> str:
        suffix = self.type_suffix(ty)
        table = {
            "+": f"ADD{suffix}",
            "-": f"SUB{suffix}",
            "*": f"MUL{suffix}",
            "/": f"DIV{suffix}",
        }
        if oper not in table:
            raise NotImplementedError(f"Aritmética no soportada: {oper}")
        return table[oper]

    def binary_bit_opcode(self, oper: str, ty: Type) -> str:
        table = {
            "&": "AND",
            "|": "OR",
            "^": "XOR",
        }
        if oper not in table:
            raise NotImplementedError(f"Bitwise no soportado: {oper}")
        return table[oper]

    # -------------------------------------------------
    # programa y declaraciones
    # -------------------------------------------------

    def visit(self, node: Program):
        self.push_scope()

        # Primera pasada: registrar nombres globales.
        for decl in node.declarations:
            if isinstance(decl, VarDecl):
                self.bind(
                    Storage(
                        decl.name,
                        decl.type,
                        is_global=True,
                        is_const=False,
                    )
                )
            elif isinstance(decl, Function):
                self.bind(Storage(decl.name, decl.return_type, is_global=True))

        # Segunda pasada: generar IR real.
        for decl in node.declarations:
            self.visit(decl)

        self.pop_scope()
        return self.program

    def visit(self, node: VarDecl):
        if self.current_function is None:
            self.emit(self.var_opcode(node.type), node.name)
            if node.value is not None:
                src = self.visit(node.value)
                self.emit(self.store_opcode(node.type), src, node.name)
            return

        self.bind(Storage(node.name, node.type, is_const=False))
        self.emit(self.alloc_opcode(node.type), node.name)
        if node.value is not None:
            src = self.visit(node.value)
            self.emit(self.store_opcode(node.type), src, node.name)

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
        for p in node.params:
            self.bind(Storage(p.name, p.type, is_param=True))
            self.emit(self.alloc_opcode(p.type), p.name)

        # node.body es una lista de statements
        if node.body is not None:
            for stmt in node.body:
                self.visit(stmt)

        # Soporte mínimo para funciones void.
        if node.return_type == VoidType:
            if not fn.instructions or fn.instructions[-1][0] != "RET":
                self.emit("RET")

        self.pop_scope()
        self.current_function = prev_fn
        self.current_return_type = prev_ret

    def visit(self, node: Block):
        self.push_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.pop_scope()

    # ParamList no es necesaria en el modelo actual
    # def visit(self, node: ParamList):
    #     return None

    def visit(self, node: Param):
        return None

    # -------------------------------------------------
    # statements
    # -------------------------------------------------

    def visit(self, node: Assignment):
        """
        Asignacion simple y compuesta.
        Soporta: =, +=, -=, *=, /=, &=, |=, ^=, <<=, >>=
        """
        if not isinstance(node.target, Identifier):
            raise NotImplementedError(
                "Starter: Assignment solo soporta Identifier por ahora"
            )

        storage = self.lookup(node.target.name)
        src = self.visit(node.value)
        self.emit(self.store_opcode(storage.ty), src, storage.name)
        return

    def visit(self, node: Print):
        regs = [self.visit(arg) for arg in node.args]
        for reg in regs:
            ty = self.infer_type(node)  # tipo inferido
            self.emit(self.print_opcode(ty), reg)

    def visit(self, node: If):
        """
        Genera IR para sentencias condicionales.
        if (cond) then_body [else else_body]
        """
        cond_reg = self.visit(node.cond)
        then_label = self.new_label()
        else_label = self.new_label()
        end_label = self.new_label()

        # Branch si la condición es falsa
        self.emit("BRANCH_FALSE", cond_reg, else_label if node.else_body else end_label)

        # Then body
        self.emit(f":{then_label}")
        if isinstance(node.then_body, list):
            for stmt in node.then_body:
                self.visit(stmt)
        else:
            self.visit(node.then_body)
        
        if node.else_body:
            self.emit("JUMP", end_label)

        # Else body (si existe)
        if node.else_body:
            self.emit(f":{else_label}")
            if isinstance(node.else_body, list):
                for stmt in node.else_body:
                    self.visit(stmt)
            else:
                self.visit(node.else_body)

        self.emit(f":{end_label}")

    def visit(self, node: While):
        """
        Genera IR para bucles while.
        while (cond) body
        """
        start_label = self.new_label()
        body_label = self.new_label()
        end_label = self.new_label()

        self.emit(f":{start_label}")
        cond_reg = self.visit(node.cond)
        self.emit("BRANCH_FALSE", cond_reg, end_label)

        self.emit(f":{body_label}")
        if isinstance(node.body, list):
            for stmt in node.body:
                self.visit(stmt)
        else:
            self.visit(node.body)
        self.emit("JUMP", start_label)

        self.emit(f":{end_label}")

    def visit(self, node: For):
        """
        Genera IR para bucles for.
        for (init; cond; update) body
        """
        if node.init:
            self.visit(node.init)

        start_label = self.new_label()
        body_label = self.new_label()
        update_label = self.new_label()
        end_label = self.new_label()

        self.emit(f":{start_label}")
        if node.cond:
            cond_reg = self.visit(node.cond)
            self.emit("BRANCH_FALSE", cond_reg, end_label)

        self.emit(f":{body_label}")
        if isinstance(node.body, list):
            for stmt in node.body:
                self.visit(stmt)
        else:
            self.visit(node.body)

        self.emit(f":{update_label}")
        if node.update:
            self.visit(node.update)
        self.emit("JUMP", start_label)

        self.emit(f":{end_label}")

    def visit(self, node: Return):
        if node.value is None:
            self.emit("RET")
            return

        reg = self.visit(node.value)
        self.emit("RET", reg)

    # -------------------------------------------------
    # expressions
    # -------------------------------------------------

    def visit(self, node: Identifier):
        storage = self.lookup(node.name)
        tmp = self.new_temp()
        self.emit(self.load_opcode(storage.ty), storage.name, tmp)
        return tmp

    def visit(self, node: ArrayAccess):
        """
        Genera IR para acceso a arreglos: arr[index]
        """
        array_storage = self.lookup(node.array.name)
        index_reg = self.visit(node.index)
        tmp = self.new_temp()

        # LOADA array_ptr, index_reg, tmp
        self.emit("LOADA", array_storage.name, index_reg, tmp)
        return tmp

    def visit(self, node: Call):
        """
        Genera IR para llamadas a funciones.
        func(arg1, arg2, ...)
        """
        # Evalúa argumentos
        arg_regs = []
        for arg in node.args:
            arg_reg = self.visit(arg)
            arg_regs.append(arg_reg)

        # Emite CALL
        tmp = self.new_temp()
        if arg_regs:
            self.emit("CALL", node.name, *arg_regs, tmp)
        else:
            self.emit("CALL", node.name, tmp)

        return tmp

    def visit(self, node: BinaryOp):
        """
        Implementación completa de operadores binarios:
        - Aritmética: + - * /
        - Comparaciones: < > <= >= == !=
        - Lógicos: && ||
        - Bitwise: & | ^ << >>
        """
        # Cortocircuito para && y ||
        if node.op == "&&":
            left_reg = self.visit(node.left)
            true_label = self.new_label()
            false_label = self.new_label()
            end_label = self.new_label()

            self.emit("BRANCH_FALSE", left_reg, false_label)
            right_reg = self.visit(node.right)
            self.emit("BRANCH_FALSE", right_reg, false_label)

            # True: cargar 1
            self.emit(f":{true_label}")
            tmp = self.new_temp()
            self.emit("MOVI", 1, tmp)
            self.emit("JUMP", end_label)

            # False: cargar 0
            self.emit(f":{false_label}")
            self.emit("MOVI", 0, tmp)

            self.emit(f":{end_label}")
            return tmp

        if node.op == "||":
            left_reg = self.visit(node.left)
            true_label = self.new_label()
            false_label = self.new_label()
            end_label = self.new_label()

            self.emit("BRANCH_TRUE", left_reg, true_label)
            right_reg = self.visit(node.right)
            self.emit("BRANCH_FALSE", right_reg, false_label)

            # True: cargar 1
            self.emit(f":{true_label}")
            tmp = self.new_temp()
            self.emit("MOVI", 1, tmp)
            self.emit("JUMP", end_label)

            # False: cargar 0
            self.emit(f":{false_label}")
            self.emit("MOVI", 0, tmp)

            self.emit(f":{end_label}")
            return tmp

        # Operandos normales
        left_reg = self.visit(node.left)
        right_reg = self.visit(node.right)
        left_ty = self.infer_type(node.left)
        out = self.new_temp()

        # Aritmética
        if node.op in {"+", "-", "*", "/"}:
            opcode = self.binary_arith_opcode(node.op, left_ty)
            self.emit(opcode, left_reg, right_reg, out)
            return out

        # Comparaciones
        if node.op in {"<", ">", "<=", ">=", "==", "!="}:
            cmp_opcode = self.cmp_opcode(left_ty)
            self.emit(cmp_opcode, left_reg, right_reg)
            self.emit("MOVZ", node.op, out)  # MOVZ carga basado en la bandera
            return out

        # Bitwise
        if node.op in {"&", "|", "^"}:
            opcode = self.binary_bit_opcode(node.op, left_ty)
            self.emit(opcode, left_reg, right_reg, out)
            return out

        # Shifts
        if node.op == "<<":
            self.emit(f"SHL{self.type_suffix(left_ty)}", left_reg, right_reg, out)
            return out
        if node.op == ">>":
            self.emit(f"SHR{self.type_suffix(left_ty)}", left_reg, right_reg, out)
            return out

        raise NotImplementedError(
            f"TODO estudiante: completar BinaryOp para operador {node.op!r}"
        )

    def visit(self, node: UnaryOp):
        """
        Genera IR para operadores unarios: +expr, -expr, !expr
        """
        operand_reg = self.visit(node.operand)
        ty = self.infer_type(node.operand)
        tmp = self.new_temp()

        if node.op == "+":
            # Unario +: simplemente retorna el mismo valor
            self.emit(self.move_opcode(ty), operand_reg, tmp)
            return tmp
        elif node.op == "-":
            # Unario -: negación
            self.emit(f"NEG{self.type_suffix(ty)}", operand_reg, tmp)
            return tmp
        elif node.op == "!":
            # Negación lógica: invierte booleano
            self.emit("NOT", operand_reg, tmp)
            return tmp
        else:
            raise NotImplementedError(f"Operador unario no soportado: {node.op}")

    def visit(self, node: Number):
        tmp = self.new_temp()
        self.emit("MOVI", int(node.value), tmp)
        return tmp

    def visit(self, node: Float):
        tmp = self.new_temp()
        self.emit("MOVF", float(node.value), tmp)
        return tmp

    def visit(self, node: Boolean):
        tmp = self.new_temp()
        self.emit("MOVI", 1 if node.value else 0, tmp)
        return tmp

    def visit(self, node: Char):
        tmp = self.new_temp()
        # Maneja caracteres simples o códigos numéricos
        if isinstance(node.value, str) and len(node.value) == 1:
            value = ord(node.value)
        elif isinstance(node.value, str):
            # Si es un string de escape, toma el primer carácter
            value = ord(node.value[0]) if node.value else 0
        else:
            value = int(node.value)
        self.emit("MOVB", value, tmp)
        return tmp

    def visit(self, node: String):
        """
        Genera IR para strings.
        Almacena strings en la tabla de cadenas global.
        """
        # Genera un label único para este string
        str_label = f"STR_{len(self.program.globals)}"
        self.program.globals.append(("STRING", str_label, node.value))

        # Carga la dirección del string en un temporal
        tmp = self.new_temp()
        self.emit("MOVS", str_label, tmp)
        return tmp

    def visit(self, node: ArrayLiteral):
        """
        Genera IR para literales de arreglos.
        [elem1, elem2, ...]
        """
        # Genera labels y almacena en globales
        arr_label = f"ARR_{len(self.program.globals)}"
        elements = [self.visit(elem) for elem in node.elements]
        self.program.globals.append(("ARRAY", arr_label, len(elements)))

        tmp = self.new_temp()
        self.emit("MOVA", arr_label, tmp)
        return tmp


# ===================================================
# demo
# ===================================================

if __name__ == "__main__":
    # Demo completa usando todas las clases del modelo
    ast = Program([
        Function(
            name="main",
            return_type=VoidType,
            params=[],
            body=Block([
                # Declaracion y asignacion simple
                VarDecl(
                    name="x",
                    type_=IntegerType,
                    value=Number(5),
                ),
                # Operadores aritmeticos
                VarDecl(
                    name="y",
                    type_=IntegerType,
                    value=BinaryOp("+", Number(3), Number(2), line=None),
                ),
                # Comparacion
                VarDecl(
                    name="z",
                    type_=BooleanType,
                    value=BinaryOp("<", Identifier("x"), Number(10), line=None),
                ),
                # Operador unario
                VarDecl(
                    name="neg",
                    type_=IntegerType,
                    value=UnaryOp("-", Number(5)),
                ),
                # Control de flujo: if
                If(
                    cond=Identifier("z"),
                    then_body=Block([
                        Print(args=[Identifier("x")]),
                    ]),
                    else_body=Block([
                        Print(args=[Number(0)]),
                    ])
                ),
                # Control de flujo: while
                While(
                    cond=BinaryOp(">", Identifier("x"), Number(0), line=None),
                    body=Block([
                        Assignment(
                            target=Identifier("x"),
                            value=BinaryOp("-", Identifier("x"), Number(1), line=None),
                        ),
                        Print(args=[Identifier("x")]),
                    ])
                ),
            ]),
        )
    ])

    ir = IRCodeGen.generate(ast)
    print(ir.format())
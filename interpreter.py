from multimethod import multimeta
from model import *
from symtab import SymbolTable


class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class Visitor(metaclass=multimeta):
    pass


class Interpreter(Visitor):
    def __init__(self):
        self.env = SymbolTable()

    def visit(self, node):
        raise NotImplementedError(type(node).__name__)

    # ================= PROGRAM =================
    def visit(self, node: Program):
        # primero registrar todo
        for d in node.declarations:
            self.visit(d)

        # 🔥 buscar main
        main_func = self.env.lookup("main")

        if main_func:
            self.visit(Call("main", []))


    # ================= BLOCK =================
    def visit(self, node: Block):
        self.env.push()
        try:
            for s in node.statements:
                self.visit(s)
        finally:
            self.env.pop()

    # ================= VARIABLES =================
    def visit(self, node: VarDecl):
        value = None
        if node.value:
            value = self.visit(node.value)
        self.env.define(node.name, value)

    def visit(self, node: Assignment):
        value = self.visit(node.value)

        if isinstance(node.target, Identifier):
            self.env.assign(node.target.name, value)
        else:
            raise RuntimeError("Asignación compleja no soportada aún")

    # ================= PRINT =================
    def visit(self, node: Print):
        output = ""

        for arg in node.args:
            val = self.visit(arg)

            if isinstance(val, str):
                # quitar comillas si vienen del parser
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]

                # interpretar escapes
                val = val.encode().decode("unicode_escape")

            output += str(val)

        print(output, end="")

    # ================= IF =================
    def visit(self, node: If):
        if self.visit(node.cond):
            for s in node.then_body:
                self.visit(s)
        elif node.else_body:
            for s in node.else_body:
                self.visit(s)

    # ================= WHILE =================
    def visit(self, node: While):
        while self.visit(node.cond):
            for s in node.body:
                self.visit(s)

    # ================= FOR =================
    def visit(self, node: For):
        self.env.push()

        if node.init:
            self.visit(node.init)

        while True:
            if node.cond and not self.visit(node.cond):
                break

            for s in node.body:
                self.visit(s)

            if node.update:
                self.visit(node.update)

        self.env.pop()

    # ================= FUNCTIONS =================

    def visit(self, node: ArrayLiteral):
        return [self.visit(e) for e in node.elements]

    def visit(self, node: ArrayAccess):
        arr = self.visit(node.array)
        idx = self.visit(node.index)

        if not isinstance(arr, list):
            raise RuntimeError("acceso a no-array")

        if idx < 0 or idx >= len(arr):
            raise RuntimeError("índice fuera de rango")

        return arr[idx]






    def visit(self, node: Function):
        self.env.define(node.name, node)

    def visit(self, node: Call):
        func = self.env.lookup(node.name)

        if not isinstance(func, Function):
            raise RuntimeError(f"{node.name} no es función")

        if len(node.args) != len(func.params):
            raise RuntimeError("Cantidad de argumentos incorrecta")

        self.env.push()

        # parámetros
        for param, arg in zip(func.params, node.args):
            value = self.visit(arg)
            self.env.define(param.name, value)

        try:
            for stmt in func.body:
                self.visit(stmt)
        except ReturnException as r:
            self.env.pop()
            return r.value

        self.env.pop()
        return None

    def visit(self, node: Return):
        value = None
        if node.value:
            value = self.visit(node.value)
        raise ReturnException(value)

    # ================= EXPRESSIONS =================

    def visit(self, node: Number):
        return node.value

    def visit(self, node: Float):
        return node.value

    def visit(self, node: Boolean):
        return node.value

    def visit(self, node: String):
        return node.value

    def visit(self, node: Char):
        return node.value

    def visit(self, node: Identifier):
        return self.env.lookup(node.name)

    def visit(self, node: BinaryOp):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if node.op == "+": return left + right
        if node.op == "-": return left - right
        if node.op == "*": return left * right
        if node.op == "/": return left / right
        if node.op == "%": return left % right

        if node.op == "==": return left == right
        if node.op == "!=": return left != right
        if node.op == "<": return left < right
        if node.op == ">": return left > right
        if node.op == "<=": return left <= right
        if node.op == ">=": return left >= right

        if node.op == "&&": return left and right
        if node.op == "||": return left or right

        raise RuntimeError(f"Operador no soportado {node.op}")

    def visit(self, node: UnaryOp):
        val = self.visit(node.operand)

        if node.op == "-": return -val
        if node.op == "!": return not val

        raise RuntimeError(f"Operador unario no soportado {node.op}")
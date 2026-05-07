# ================= BASE NODE =================

class Node:
    def accept(self, visitor):
        return visitor.visit(self)


# ================= PROGRAM =================

class Program(Node):
    def __init__(self, declarations):
        self.declarations = declarations


# ================= TYPES =================

class Type:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Type) and self.name == other.name

    def __hash__(self):
        return hash(self.name)   # 🔥 SOLUCIÓN GLOBAL

    def __str__(self):
        return self.name

# Tipos básicos
IntegerType = Type("integer")
FloatType = Type("float")
BooleanType = Type("boolean")
StringType = Type("string")
CharType = Type("char")
VoidType = Type("void")


# Array
class ArrayType(Type):
    def __init__(self, base, size=None):
        super().__init__("array")
        self.base = base
        self.size = size

    def __eq__(self, other):
        return (
            isinstance(other, ArrayType)
            and self.base == other.base
        )

    def __hash__(self):
        return hash(("array", self.base))   # 🔥 CLAVE PARA EVITAR ERROR

    def __str__(self):
        if self.size is not None and isinstance(self.size, int):
            return f"array[{self.size}] of {self.base}"
        return f"array of {self.base}"

# Function
class FunctionType(Type):
    def __init__(self, return_type, param_types):
        super().__init__("function")
        self.return_type = return_type
        self.param_types = param_types

    def __eq__(self, other):
        return (
            isinstance(other, FunctionType)
            and self.return_type == other.return_type
            and self.param_types == other.param_types
        )

    def __hash__(self):
        return hash(("function", self.return_type, tuple(self.param_types)))

    def __str__(self):
        return f"function({self.param_types}) -> {self.return_type}"
        return f"function({self.param_types}) -> {self.return_type}"


# ================= DECLARATIONS =================

class VarDecl(Node):
    def __init__(self, name, type_, value=None):
        self.name = name
        self.type = type_
        self.value = value


class Param(Node):
    def __init__(self, name, type_):
        self.name = name
        self.type = type_


class Function(Node):
    def __init__(self, name, return_type, params, body):
        self.name = name
        self.return_type = return_type
        self.params = params
        self.body = body   # lista de statements o None


# ================= STATEMENTS =================

class Block(Node):
    def __init__(self, statements):
        self.statements = statements


class Assignment(Node):
    def __init__(self, target, value):
        self.target = target
        self.value = value


class If(Node):
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body


class While(Node):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class For(Node):
    def __init__(self, init, cond, update, body):
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body


class Return(Node):
    def __init__(self, value):
        self.value = value


class Print(Node):
    def __init__(self, args):
        self.args = args


# ================= EXPRESSIONS =================

class Identifier(Node):
    def __init__(self, name):
        self.name = name
        self.type = None


class Number(Node):
    def __init__(self, value):
        self.value = value
        self.type = IntegerType


class Float(Node):
    def __init__(self, value):
        self.value = value
        self.type = FloatType


class Boolean(Node):
    def __init__(self, value):
        self.value = value
        self.type = BooleanType


class String(Node):
    def __init__(self, value):
        self.value = value
        self.type = StringType


class Char(Node):
    def __init__(self, value):
        self.value = value
        self.type = CharType


class BinaryOp:
    def __init__(self, op, left, right, line=None):
        self.op = op
        self.left = left
        self.right = right
        self.line = line   


class UnaryOp(Node):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
        self.type = None


class Call(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args
        self.type = None


# ================= ARRAYS =================

class ArrayLiteral(Node):
    def __init__(self, elements):
        self.elements = elements
        self.type = None


class ArrayAccess(Node):
    def __init__(self, array, index):
        self.array = array
        self.index = index
        self.type = None

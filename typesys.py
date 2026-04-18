from model import *

def check_binop(op, left, right):

    # 🔥 ARITMÉTICOS
    if op in ("+", "-", "*", "/", "%"):
        if left == IntegerType and right == IntegerType:
            return IntegerType
        if left == FloatType and right == FloatType:
            return FloatType
        return None

    # 🔥 RELACIONALES
    if op in ("<", ">", "<=", ">="):
        if left == IntegerType and right == IntegerType:
            return BooleanType
        if left == FloatType and right == FloatType:
            return BooleanType
        return None

    # 🔥 IGUALDAD
    if op in ("==", "!="):
        if left == right:
            return BooleanType
        return None

    # 🔥 LÓGICOS
    if op in ("&&", "||"):
        if left == BooleanType and right == BooleanType:
            return BooleanType
        return None

    return None
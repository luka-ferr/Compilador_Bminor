"""
checker.py
==========

Analizador semántico para el lenguaje B-Minor.

Este módulo implementa la fase de verificación semántica del compilador.
Recorre el Árbol de Sintaxis Abstracta (AST) generado por el parser y valida:

- Declaración previa de identificadores.
- Manejo correcto de alcances (scopes).
- Compatibilidad de tipos.
- Uso correcto de funciones.
- Validación de sentencias return.
- Condiciones booleanas en estructuras de control.
- Uso correcto de arreglos.
- Operadores válidos.

Diseño general:
---------------
Se implementa el patrón Visitor, donde cada tipo de nodo del AST posee
un método específico visit_<Nodo>().

Ejemplo:
    visit_Function()
    visit_If()
    visit_Assignment()

Dependencias:
-------------
model.py     -> Define nodos AST y tipos.
symtab.py    -> Tabla de símbolos con scopes anidados.
typesys.py   -> Reglas semánticas para operadores binarios.
multimethod  -> Soporte para despacho múltiple.

Autor:
------
Luis Fernando Caicedo
"""

from model import *
from symtab import Symtab
from typesys import check_binop
from multimethod import multimeta


class Visitor(metaclass=multimeta):
    """
    Clase base Visitor.

    Permite usar múltiples firmas del método visit().
    """
    pass


class Checker(Visitor):
    """
    Analizador semántico principal.

    Atributos:
    ----------
    env : Symtab
        Tabla de símbolos actual.

    errors : list[str]
        Lista de errores encontrados.

    error_set : set[str]
        Conjunto auxiliar para evitar duplicados.

    current_function : Function | None
        Función actual durante el recorrido.
        Se usa para validar sentencias return.
    """

    def __init__(self):
        """
        Inicializa el checker.
        """
        self.env = Symtab("global")
        self.errors = []
        self.error_set = set()
        self.current_function = None

    # ==========================================================
    # VISITOR GENERAL
    # ==========================================================

    def visit(self, node):
        """
        Despacha dinámicamente al método correspondiente.

        Ejemplo:
            Function -> visit_Function()
            If       -> visit_If()

        Si no existe método específico, usa generic_visit().
        """
        method = f"visit_{type(node).__name__}"
        return getattr(self, method, self.generic_visit)(node)

    def visit(self, node: list):
        """
        Recorre listas de nodos.
        """
        for n in node:
            self.visit(n)

    def visit_list(self, nodes):
        """
        Visita una lista y retorna el último resultado.
        """
        result = None
        for n in nodes:
            result = self.visit(n)
        return result

    def generic_visit(self, node):
        """
        Método por defecto si no existe visit específico.
        """
        return None

    # ==========================================================
    # MANEJO DE ERRORES
    # ==========================================================

    def error(self, msg, node=None):
        """
        Registra error semántico.

        Parámetros:
        -----------
        msg : str
            Mensaje de error.

        node : Node | None
            Nodo donde ocurrió el error.
            Si posee atributo line, se muestra línea.

        Evita duplicados.
        """
        if node and hasattr(node, "line"):
            full = f"error: {msg} en la línea {node.line}"
        else:
            full = f"error: {msg}"

        if full not in self.error_set:
            self.error_set.add(full)
            self.errors.append(full)

    # ==========================================================
    # SCOPES / ALCANCES
    # ==========================================================

    def push(self, name="scope"):
        """
        Entra a un nuevo scope.
        """
        self.env = Symtab(name, self.env)

    def pop(self):
        """
        Sale del scope actual.
        """
        self.env = self.env.parent

    # ==========================================================
    # TABLA DE SÍMBOLOS
    # ==========================================================

    def lookup(self, name, node=None):
        """
        Busca identificador en scopes activos.

        Si no existe, genera error.
        """
        value = self.env.get(name)

        if value is None:
            self.error(f"símbolo '{name}' no definido", node)

        return value

    def define(self, name, type_):
        """
        Registra símbolo en scope actual.

        Detecta redefiniciones o conflictos.
        """
        try:
            self.env.add(name, type_)
        except Exception as e:
            self.error(str(e))

    # ==========================================================
    # PROGRAMA
    # ==========================================================

    def visit_Program(self, node):
        """
        Analiza programa completo.

        Fases:
        ------
        1. Registrar firmas de funciones.
        2. Analizar variables globales.
        3. Analizar cuerpos de funciones.
        """

        # Registrar funciones primero
        for d in node.declarations:
            if isinstance(d, Function):
                func_type = FunctionType(
                    d.return_type,
                    [p.type for p in d.params]
                )
                self.define(d.name, func_type)

        # Variables y demás declaraciones
        for d in node.declarations:
            if not isinstance(d, Function):
                self.visit(d)

        # Cuerpos de funciones
        for d in node.declarations:
            if isinstance(d, Function):
                self.visit(d)

    # ==========================================================
    # DECLARACIONES
    # ==========================================================

    def visit_VarDecl(self, node):
        """
        Analiza declaración de variable.

        Verifica:
        - registro del símbolo
        - compatibilidad con inicialización
        """
        self.define(node.name, node.type)

        if node.value:
            val_type = self.visit(node.value)

            if isinstance(node.type, ArrayType) and isinstance(val_type, ArrayType):
                if node.type.base != val_type.base:
                    self.error("tipos incompatibles en array", node)

            elif val_type != node.type:
                self.error(
                    f"no se puede asignar {val_type} a {node.type}",
                    node
                )

    def visit_Function(self, node):
        """
        Analiza función.

        Verifica:
        - nuevo scope
        - parámetros
        - cuerpo
        - retorno obligatorio
        """
        if node.body is None:
            return

        self.push()
        self.current_function = node

        for p in node.params:
            self.define(p.name, p.type)

        for stmt in node.body:
            self.visit(stmt)

        if node.return_type != VoidType:
            if not self.must_return(node.body):
                self.error(
                    f"la función '{node.name}' debe retornar en todos los caminos",
                    node
                )

        self.pop()
        self.current_function = None

    def must_return(self, stmts):
        for stmt in stmts:

            if isinstance(stmt, Return):
                return True

            elif isinstance(stmt, If):
                then_returns = self.must_return([stmt.then_body] if not isinstance(stmt.then_body, list) else stmt.then_body)

                else_returns = False
                if stmt.else_body:
                    else_returns = self.must_return([stmt.else_body] if not isinstance(stmt.else_body, list) else stmt.else_body)

                # 🔥 CLAVE: ambos caminos deben retornar
                return then_returns and else_returns

            elif isinstance(stmt, Block):
                if self.must_return(stmt.statements):
                    return True

        return False

    def visit_ArrayAccess(self, node):
        arr_type = self.visit(node.array)
        index_type = self.visit(node.index)

        if index_type != IntegerType:
            self.error("el índice debe ser entero", node)
            return None

        if not isinstance(arr_type, ArrayType):
            self.error("no es un arreglo", node)
            return None

        return arr_type.base
    
    def visit_ArrayLiteral(self, node):
        if not node.elements:
            return None

        first_type = self.visit(node.elements[0])

        for elem in node.elements:
            t = self.visit(elem)
            if t != first_type:
                self.error("elementos del array con tipos distintos", node)
                return None

        return ArrayType(first_type)

    def visit_Call(self, node):
        func_type = self.lookup(node.name, node)

        if not isinstance(func_type, FunctionType):
            self.error(f"'{node.name}' no es una función", node)
            return None

        # Verificar argumentos
        if len(node.args) != len(func_type.param_types):
            self.error("número incorrecto de argumentos", node)
            return func_type.return_type

        for arg, expected in zip(node.args, func_type.param_types):
            arg_type = self.visit(arg)

            if arg_type != expected:
                self.error(
                    f"argumento incompatible: se esperaba {expected} pero se recibió {arg_type}",
                    node
                )

        return func_type.return_type
    
    # ==========================================================
    # BLOQUES
    # ==========================================================

    def visit_Block(self, node):
        """
        Cada bloque crea nuevo scope.
        """
        self.push()

        for s in node.statements:
            self.visit(s)

        self.pop()

    # ==========================================================
    # SENTENCIAS
    # ==========================================================

    def visit_Assignment(self, node):
        """
        Valida asignación.
        """
        if not isinstance(node.target, Identifier):
            self.error("lado izquierdo inválido en asignación", node)
            return

        t1 = self.lookup(node.target.name, node)
        t2 = self.visit(node.value)

        if t1 and t2 and t1 != t2:
            self.error(
                f"no se puede asignar {t2} a {t1}",
                node
            )

    def visit_Return(self, node):
        """
        Valida return según tipo de función actual.
        """
        if not self.current_function:
            self.error("return fuera de función", node)
            return

        expected = self.current_function.return_type

        if node.value:
            val_type = self.visit(node.value)

            if expected == VoidType:
                self.error("no se debe retornar valor en función void", node)

            elif val_type != expected:
                self.error("tipo de retorno incorrecto", node)

        else:
            if expected != VoidType:
                self.error("falta valor en return", node)

    def visit_Print(self, node):
        """
        Analiza argumentos de print.
        """
        for a in node.args:
            self.visit(a)

    def visit_If(self, node):
        """
        Condición debe ser boolean.
        """
        cond = self.visit(node.cond)

        if cond != BooleanType:
            self.error("la condición del if debe ser boolean", node)

        self.visit(node.then_body)

        if node.else_body:
            self.visit(node.else_body)

    def visit_While(self, node):
        """
        Condición while debe ser boolean.
        """
        cond = self.visit(node.cond)

        if cond != BooleanType:
            self.error("la condición del while debe ser boolean", node)

        self.visit(node.body)

    def visit_For(self, node):
        """
        Analiza for.
        """
        self.push()

        if node.init:
            self.visit(node.init)

        cond = self.visit(node.cond)

        if cond != BooleanType:
            self.error("la condición del for debe ser boolean", node)

        if node.update:
            self.visit(node.update)

        self.visit(node.body)

        self.pop()

    # ==========================================================
    # LITERALES / IDENTIFICADORES
    # ==========================================================

    def visit_Number(self, node):
        node.type = IntegerType
        return node.type

    def visit_Float(self, node):
        node.type = FloatType
        return node.type

    def visit_String(self, node):
        node.type = StringType
        return node.type

    def visit_Char(self, node):
        node.type = CharType
        return node.type

    def visit_Boolean(self, node):
        node.type = BooleanType
        return node.type

    def visit_Identifier(self, node):
        t = self.lookup(node.name, node)
        node.type = t
        return t

    # ==========================================================
    # OPERADORES
    # ==========================================================

    def visit_BinaryOp(self, node):
        """
        Valida operador binario.
        """
        l = self.visit(node.left)
        r = self.visit(node.right)

        result = check_binop(node.op, l, r)

        if result is None:
            self.error("operación inválida", node)
            return None

        node.type = result
        return result

    def visit_UnaryOp(self, node):
        """
        Valida operadores unarios.
        """
        t = self.visit(node.operand)

        if node.op == "-" and t in (IntegerType, FloatType):
            node.type = t
            return t

        if node.op == "!" and t == BooleanType:
            node.type = BooleanType
            return node.type

        self.error("operador unario inválido", node)
        return None

import re
from model import *

# ================= TOKENIZER =================

def tokenize(src):
    token_spec = [
        ("COMMENT1", r'//.*'),
        ("COMMENT2", r'/\*[\s\S]*?\*/'),
        ("INC", r'\+\+'),
        ("DEC", r'--'),
        ("LOGIC", r'&&|\|\|'),
        ("NUMBER", r'\d+(\.\d+)?'),
        ("STRING", r'"[^"]*"'),
        ("CHAR", r"'(\\.|[^\\'])+'"),
        ("ID", r'[A-Za-z_][A-Za-z0-9_]*'),
        ("OP", r'==|!=|<=|>=|<|>|\+|-|\*|/|=|!|%'),
        ("SYM", r'[{}()\[\],;:]'),
        ("SKIP", r'[ \t]+'),
        ("NEWLINE", r'\n'),
    ]

    tok_regex = "|".join(f"(?P<{n}>{r})" for n, r in token_spec)

    tokens = []
    line = 1

    for m in re.finditer(tok_regex, src):
        kind = m.lastgroup
        value = m.group()

        if kind == "NEWLINE":
            line += 1
            continue

        if kind in ("SKIP", "COMMENT1", "COMMENT2"):
            continue

        tokens.append((value, line))

    return tokens


# ================= PARSER =================

def parse(source):
    tokens = tokenize(source)
    pos = 0

    def peek():
        return tokens[pos][0] if pos < len(tokens) else None

    def line():
        return tokens[pos][1] if pos < len(tokens) else None

    def peek2():
        return tokens[pos+1][0] if pos+1 < len(tokens) else None

    def peek3():
        return tokens[pos+2][0] if pos+2 < len(tokens) else None

    def consume(expected=None):
        nonlocal pos
        tok = tokens[pos] if pos < len(tokens) else None

        if tok is None:
            raise SyntaxError(f"EOF inesperado en la línea {line()}")

        value, ln = tok

        if expected and value != expected:
            raise SyntaxError(f"Se esperaba '{expected}' pero se encontró '{value}' en la línea {ln}")

        pos += 1
        return value, ln

    # ================= TYPES =================

    def parse_type():
        if peek() == "array":
            consume("array")
            consume("[")
            size = None
            if peek() != "]":
                size = parse_expr()
            consume("]")
            base = parse_type()
            return ArrayType(base, size)

        tok = peek()

        types = {
            "integer": IntegerType,
            "float": FloatType,
            "boolean": BooleanType,
            "string": StringType,
            "char": CharType,
            "void": VoidType
        }

        if tok in types:
            consume()
            return types[tok]

        # 🔥 CLAVE: no consumir si no es tipo válido
        raise SyntaxError(f"Tipo desconocido: {tok} en la línea {line()}")

    # ================= EXPRESSIONS =================

    def parse_primary():
        tok = peek()

        if tok == "(":
            consume("(")
            e = parse_expr()
            consume(")")
            return e

        if tok in ("true", "false"):
            v, ln = consume()
            n = Boolean(v == "true")
            n.line = ln
            return n

        if re.match(r'^\d+\.\d+$', tok):
            v, ln = consume()
            n = Float(float(v))
            n.line = ln
            return n

        if tok.isdigit():
            v, ln = consume()
            n = Number(int(v))
            n.line = ln
            return n

        if tok.startswith('"'):
            v, ln = consume()
            n = String(v)
            n.line = ln
            return n

        if tok.startswith("'"):
            v, ln = consume()
            n = Char(v)
            n.line = ln
            return n

        if tok == "{":
            _, ln = consume("{")
            elems = []

            while peek() != "}":
                elems.append(parse_expr())
                if peek() == ",":
                    consume(",")

            consume("}")
            n = ArrayLiteral(elems)
            n.line = ln
            return n

        if tok.isidentifier():
            name, ln = consume()

            # call
            if peek() == "(":
                consume("(")
                args = []
                while peek() != ")":
                    args.append(parse_expr())
                    if peek() == ",":
                        consume(",")
                consume(")")
                n = Call(name, args)
                n.line = ln
                return n

            n = Identifier(name)
            n.line = ln

            while peek() == "[":
                consume("[")
                idx = parse_expr()
                consume("]")
                n = ArrayAccess(n, idx)
                n.line = ln

            return n

        raise SyntaxError(f"Token inesperado '{tok}' en la línea {line()}")

    def parse_unary():
        if peek() in ("-", "!"):
            op, ln = consume()
            n = UnaryOp(op, parse_unary())
            n.line = ln
            return n
        return parse_primary()

    def bin_layer(parse_next, ops):
        def f():
            node = parse_next()
            while peek() in ops:
                op, ln = consume()
                node = BinaryOp(op, node, parse_next())
                node.line = ln
            return node
        return f

    parse_mul = bin_layer(parse_unary, ("*", "/", "%"))
    parse_add = bin_layer(parse_mul, ("+", "-"))
    parse_rel = bin_layer(parse_add, ("<", ">", "<=", ">="))
    parse_eq  = bin_layer(parse_rel, ("==", "!="))
    parse_logic = bin_layer(parse_eq, ("&&", "||"))

    def parse_expr():
        return parse_logic()

    # ================= STATEMENTS =================

    def parse_block():
        _, ln = consume("{")
        stmts = []

        while peek() != "}":
            stmt = parse_statement()
            if stmt is not None:
                stmts.append(stmt)

        consume("}")
        b = Block(stmts)
        b.line = ln
        return b


    def parse_vardecl():
        name, ln = consume()

        if peek() != ":":
            raise SyntaxError(f"Se esperaba ':' después de '{name}' en la línea {ln}")

        consume(":")
        t = parse_type()

        val = None
        if peek() == "=":
            consume("=")
            val = parse_expr()

        consume(";")

        n = VarDecl(name, t, val)
        n.line = ln
        return n

    def parse_assignment():
        target = parse_primary()

        if peek() == "=":
            _, ln = consume("=")
            val = parse_expr()
            consume(";")
            n = Assignment(target, val)
            n.line = ln
            return n

        if peek() == "++":
            _, ln = consume("++")
            consume(";")
            one = Number(1)
            one.line = ln

            binop = BinaryOp("+", target, one)
            binop.line = ln

            n = Assignment(target, binop)
            n.line = ln

            
            return n

        if peek() == "--":
            _, ln = consume("--")
            consume(";")
            one = Number(1)
            one.line = ln

            binop = BinaryOp("-", target, one)
            binop.line = ln

            n = Assignment(target, binop)
            n.line = ln

            return n

        raise SyntaxError(f"Asignación inválida en la línea {line()}")

    def parse_if():
        
        _, ln = consume("if")
        consume("(")
        cond = parse_expr()
        consume(")")

        
        if peek() == "{":
            then_b = parse_block().statements
        else:
            then_b = [parse_statement()]

        else_b = None
        if peek() == "else":
            consume("else")
            if peek() == "{":
                else_b = parse_block().statements
            else:
                else_b = [parse_statement()]

        n = If(cond, then_b, else_b)
        n.line = ln
        return n

    def parse_while():
        
        _, ln = consume("while")
        consume("(")
        cond = parse_expr()
        consume(")")

        if peek() == "{":
            body = parse_block().statements
        else:
            body = [parse_statement()]

        n = While(cond, body)
        n.line = ln
        return n

    def parse_for():
        _, ln = consume("for")
        consume("(")

        init = None
        if peek() != ";":
            target = parse_primary()
            consume("=")
            val = parse_expr()
            init = Assignment(target, val)
            init.line = ln
        consume(";")

        cond = parse_expr()
        consume(";")

        update = None
        if peek() != ")":
            target = parse_primary()

            if peek() == "=":
                consume("=")
                val = parse_expr()
                update = Assignment(target, val)

            elif peek() == "++":
                consume("++")
                one = Number(1)
                one.line = ln
                one = Number(1)
                one.line = ln

                binop = BinaryOp("+", target, one)
                binop.line = ln

                update = Assignment(target, binop)
                update.line = ln


            elif peek() == "--":
                consume("--")
                one = Number(1)
                one.line = ln

                binop = BinaryOp("-", target, one)
                binop.line = ln

                update = Assignment(target, binop)
                update.line = ln

            

        consume(")")

        # 🔥 FLEXIBLE
        if peek() == "{":
            body = parse_block().statements
        else:
            body = [parse_statement()]

        n = For(init, cond, update, body)
        n.line = ln
        return n

    
    def parse_return():
        _, ln = consume("return")
        
        val = None
        if peek() != ";":
            try:
                val = parse_expr()
            except SyntaxError:
                raise SyntaxError(f"línea {ln} Expresión inválida en return")
        
        if peek() != ";":
            tok = peek()
            raise SyntaxError(f"línea {ln} Se esperaba ';' después del return")
        
        consume(";")
        
        n = Return(val)
        n.line = ln
        return n

    def parse_print():
        _, ln = consume("print")
        args = []
        while peek() != ";":
            args.append(parse_expr())
            if peek() == ",":
                consume(",")
        consume(";")
        n = Print(args)
        n.line = ln
        return n

    def parse_statement():
        tok = peek()

        # vacío
        if tok == ";":
            consume(";")
            return None

        if tok == "{": return parse_block()
        if tok == "if": return parse_if()
        if tok == "while": return parse_while()
        if tok == "for": return parse_for()
        if tok == "return": return parse_return()
        if tok == "print": return parse_print()

        # 🔥 CLAVE REAL: detectar declaración bien
        if peek2() == ":":
            return parse_vardecl()

        # 🔥 NUEVO: detectar tipo sin :
        if tok in ("integer", "float", "boolean", "string", "char"):
            raise SyntaxError(f"Declaración inválida en la línea {line()}")

        # assignment
        if peek2() == "=" or peek2() in ("++", "--"):
            return parse_assignment()

        # 🔥 fallback expresión
        expr = parse_expr()
        consume(";")
        return expr

    # ================= FUNCTION =================

    def parse_function():
        name, ln = consume()
        consume(":")
        consume("function")

        ret = parse_type()

        consume("(")
        params = []
        while peek() != ")":
            pname, _ = consume()
            consume(":")
            ptype = parse_type()
            params.append(Param(pname, ptype))
            if peek() == ",":
                consume(",")
        consume(")")

        if peek() == ";":
            consume(";")
            n = Function(name, ret, params, None)
            n.line = ln
            return n

        consume("=")
        body = parse_block()

        n = Function(name, ret, params, body.statements)
        n.line = ln
        return n

    # ================= PROGRAM =================

    decls = []

    while peek():
        if peek2() == ":" and peek3() == "function":
            decls.append(parse_function())
        else:
            decls.append(parse_vardecl())

    return Program(decls)
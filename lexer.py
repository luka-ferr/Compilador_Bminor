import re

# =========================
# TOKEN DEFINITIONS
# =========================

TOKEN_SPEC = [
    # --- COMMENTS ---
    ("COMMENT1", r'//.*'),
    ("COMMENT2", r'/\*[\s\S]*?\*/'),

    # --- INCREMENT / DECREMENT ---
    ("INC", r'\+\+'),
    ("DEC", r'--'),

    # --- LOGICAL OPS ---
    ("LOGIC", r'&&|\|\|'),

    # --- RELATIONAL / EQUALITY ---
    ("EQ", r'==|!='),
    ("REL", r'<=|>=|<|>'),

    # --- ASSIGN ---
    ("ASSIGN", r'='),

    # --- ARITHMETIC ---
    ("OP", r'\+|-|\*|/|%'),

    # --- LITERALS ---
    ("FLOAT", r'\d+\.\d+'),
    ("INT", r'\d+'),

    # STRING con escapes
    ("STRING", r'"(\\.|[^"\\])*"'),

    # CHAR con escapes (IMPORTANTE: soporta '\n', '\0x41', etc.)
    ("CHAR", r"'(\\x[0-9A-Fa-f]+|\\.|[^\\'])'"),

    # --- IDENTIFIERS / KEYWORDS ---
    ("ID", r'[A-Za-z_][A-Za-z0-9_]*'),

    # --- SYMBOLS ---
    ("SYM", r'[{}()\[\],;:]'),

    # --- WHITESPACE ---
    ("SKIP", r'[ \t\r\n]+'),

    # --- ERROR ---
    ("MISMATCH", r'.'),
]

# Compilar regex
TOK_REGEX = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
MASTER = re.compile(TOK_REGEX)


# =========================
# KEYWORDS
# =========================

KEYWORDS = {
    "if", "else", "for", "while", "return",
    "print",
    "function",
    "true", "false",
    "integer", "float", "boolean", "char", "string", "void",
    "array"
}


# =========================
# TOKEN CLASS
# =========================

class Token:
    def __init__(self, type_, value, line, column):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"{self.type}({self.value}) at {self.line}:{self.column}"


# =========================
# TOKENIZER
# =========================

def tokenize(code):
    tokens = []
    line = 1
    col = 1

    for match in MASTER.finditer(code):
        kind = match.lastgroup
        value = match.group()

        if kind == "SKIP":
            line += value.count("\n")
            if "\n" in value:
                col = 1
            else:
                col += len(value)
            continue

        if kind in ("COMMENT1", "COMMENT2"):
            line += value.count("\n")
            continue

        if kind == "ID" and value in KEYWORDS:
            kind = value.upper()

        if kind == "MISMATCH":
            raise SyntaxError(f"Token inválido '{value}' en línea {line}")

        tokens.append(Token(kind, value, line, col))
        col += len(value)

    tokens.append(Token("EOF", "", line, col))
    return tokens
import sys
import os

from lexer import tokenize
from parser import parse
from checker import Checker
from rich import print

# opcional
try:
    from interpreter import Interpreter
    HAS_INTERPRETER = True
except:
    HAS_INTERPRETER = False


# ================= LEER ARCHIVO =================

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return f.read()


# ================= EJECUTAR 1 ARCHIVO =================

def run_file(path, run_interpreter=True):
    print(f"\n📄 Ejecutando: {path}")

    try:
        source = read_file(path)

        # ========= PARSER =========
        ast = parse(source)

        # ========= CHECKER =========
        checker = Checker()
        checker.visit(ast)

        if checker.errors:
            for err in checker.errors:
                print(err)   # 🔥 sin duplicar "error:"
            print("\n[red]Semantic check: failed[/red]")
            return False

        print("\n[green]Semantic check: success[/green]")

        # ========= INTERPRETER =========
        if run_interpreter and HAS_INTERPRETER:
            interpreter = Interpreter()
            interpreter.visit(ast)

        return True

    except SyntaxError as e:
        print("Error de sintaxis")
        print(f"error: {e}")
        return False

    except Exception as e:
        print(f"error: {e}")
        print("error inesperado")
        return False


# ================= EJECUTAR CARPETA =================

def run_folder(folder):
    if not os.path.isdir(folder):
        print(f"error: '{folder}' no es una carpeta válida")
        return

    files = sorted(os.listdir(folder))

    total = 0
    passed = 0

    is_good = "good" in folder.lower()

    for f in files:
        if f.startswith("._"):
            continue

        if not f.endswith(".bminor"):
            continue

        total += 1
        path = os.path.join(folder, f)

        ok = run_file(path, run_interpreter=False)

        if is_good:
            if ok:
                passed += 1
        else:
            if not ok:
                passed += 1

    print("\n==========================")
    print(f"RESULTADO: {passed}/{total} correctos")
    print("==========================\n")


# ================= MAIN =================

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python main.py archivo.bminor")
        print("  python main.py carpeta/")
        return

    path = sys.argv[1]

    # 🔥 SI ES CARPETA → correr todos
    if os.path.isdir(path):
        run_folder(path)
        return

    # 🔥 SI ES ARCHIVO → correr uno
    if os.path.isfile(path):
        run_file(path)
        return

    print(f"error: ruta inválida '{path}'")


if __name__ == "__main__":
    main()

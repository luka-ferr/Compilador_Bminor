# Analizador Semántico B-Minor

## Descripción

Analizador Semántico para B-Minor
📌 Descripción

Este proyecto implementa un analizador semántico para el lenguaje B-Minor, desarrollado en Python como parte del curso de Compiladores.

El analizador semántico recibe un AST (Abstract Syntax Tree) generado por el parser y verifica la correcta semántica del programa, incluyendo:

uso correcto de variables,
manejo de tipos,
verificación de funciones,
control de alcances léxicos,
validación de expresiones.
---

## Funcionalidades

* Tabla de símbolos con **alcance léxico**
* Chequeo de:

  * variables no declaradas
  * redeclaraciones
  * asignaciones incompatibles
* Validación de tipos en:

  * expresiones aritméticas, relacionales y lógicas
  * condiciones (`if`, `while`, `for`)

* Verificación de funciones:
  * número de argumentos
  * tipos de argumentos
  * tipo de retorno

* Soporte para **arreglos**:
  * índice entero
  * consistencia de tipos

---


  # Chequeos semánticos implementados

# Variables
Uso de variables no declaradas
Redeclaración en el mismo scope
Asignaciones incompatibles

# Tipos y expresiones
Operadores aritméticos (+ - * / %)
Operadores relacionales (< > <= >=)
Operadores lógicos (&& || !)
Validación de tipos en expresiones


 # Funciones

Verificación de número de argumentos
Verificación de tipos de argumentos
Validación del tipo de retorno
Verificación de retorno en funciones no void

 # Arreglos
Índices deben ser enteros
Acceso válido a estructuras tipo array
Consistencia de tipos en arreglos



## Estructura

```text
bminor/
├── lexer.py
├── parser.py
├── model.py
├── symtab.py
├── checker.py
├── main.py
└── tests/
    ├── good/
    └── bad/
```

hay carpetas y archivos extra como interpreter (la idea era hacer los prints de los programas pero fallo) y vizualizer y typesy en la carpeta bminor que no son parte del proyecto y estos se hicieros para mejorar el trabajo del analizador semántico pero las pruebas fallaron entoces el proyecto funciona normalmente se dejan para cuando vengan los siguientes proyectos arreglarlos y ponerlos a funcionar correctamente
---

Diseño del Analizador Semántico
# Patrón Visitor

El recorrido del AST se implementa usando el patrón Visitor con la librería multimethod.

Se utiliza un enfoque híbrido:

Clase base Visitor con multimeta
Método visit() que realiza despacho dinámico
Métodos específicos como:
visit_If
visit_Assignment
visit_BinaryOp

# Tabla de símbolos

La tabla de símbolos (Symtab) maneja:

alcances anidados (scope chaining),
inserción de variables y funciones,
búsqueda respetando alcance léxico,
detección de redeclaraciones.

Cada símbolo almacena:

nombre
tipo
contexto de declaración

 # Sistema de tipos

El lenguaje es fuertemente tipado.

Tipos soportados:

integer
float
boolean
string
char
void
array[T]

 # Manejo de errores
Los errores se acumulan (no se detiene en el primero)
Cada error incluye:
descripción clara
número de línea

Ejemplo:

error: símbolo 'x' no definido en la línea 8
error: no se puede asignar boolean a integer en la línea 12


## Requisitos

* Python 3
* Librería:

```bash
pip install multimethod rich graphviz 
```

---

## Entorno virtual

El proyecto fue ejecutado usando un entorno virtual (`venv`) con todas las dependencias instaladas.

Creación y activación:

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

## Ejecución

```bash
para ejecutar todos los tests: good y bad se usan los siguientes comandos
python main.py tests/good
python main.py tests/bad

si se quiere correr un solo archivo se usa el siguiente comando 
python main.py tests/good/good0.bminor 
python main.py tests/bad/bad3.bminor
```
---

## Salida esperada

Programa correcto:

```text
semantic check: success
```

Programa con errores:

```text
error: descripción del error en la línea X
semantic check: failed
```
---

## Implementación

* Recorrido del AST mediante patrón **Visitor**
* Uso de `multimethod` (implementación híbrida)
* Tipos anotados en los nodos (`node.type`)
* Manejo de errores acumulativo (no se detiene en el primero)
---

## Pruebas

* `tests/good/`: programas válidos
* `tests/bad/`: programas con errores

Resultado:

```text
10/10 correctos
```

---

## Autores

Manuel Alejandro Gomez Briceño 
Fernando Caicedo 
Curso de Compiladores






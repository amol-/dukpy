dukpy
=====

.. image:: https://img.shields.io/travis/amol-/dukpy/master.svg?label=Linux%20build%20%40%20Travis%20CI
    :target: https://travis-ci.org/amol-/dukpy

.. image:: https://img.shields.io/appveyor/ci/amol-/dukpy/master.svg?label=Windows%20build%20%40%20Appveyor
    :target: https://ci.appveyor.com/project/amol-/dukpy

.. image:: https://coveralls.io/repos/amol-/dukpy/badge.png?branch=master
    :target: https://coveralls.io/r/amol-/dukpy?branch=master

.. image:: https://img.shields.io/pypi/v/dukpy.svg
   :target: https://pypi.org/p/dukpy


DukPy é um simples interpretador javascript para Python construído sobre o
duktape engine **sem qualquer dependência externa**.
Ele vem com um monte de transpilers imbutidos por conveniência: 

    - *CoffeeScript*
    - *BabelJS*
    - *TypeScript*
    - *JSX*
    - *LESS*

O Dukpy foi testado no ** Python 2.7 ** e ** Python 3.4 **, dukpy
atualmente não está pronta para produção e pode realmente causar 
acidente no seu programa como é principalmente implementado em C.


Compilador CoffeeScript 
---------------------

Usar o compilador coffeescript é tão fácil quanto funciona:

.. code:: python

    >>> import dukpy
    >>> dukpy.coffee_compile('''
    ...     fill = (container, liquid = "coffee") ->
    ...         "Filling the #{container} with #{liquid}..."
    ... ''')
    '(function() {\n  var fill;\n\n  fill = function*(container, liquid) {\n    if (liquid == null) {\n      liquid = "coffee";\n    }\n    return "Filling the " + container + " with " + liquid + "...";\n  };\n\n}).call(this);\n'

TypeScript Transpiler
---------------------

O compilador TypeScript pode ser usado através do
função `` dukpy.typescript_compile``:

.. code:: python

    >>> import dukpy
    >>> dukpy.typescript_compile('''
    ... class Greeter {
    ...     constructor(public greeting: string) { }
    ...     greet() {
    ...         return "<h1>" + this.greeting + "</h1>";
    ...     }
    ... };
    ...
    ... var greeter = new Greeter("Hello, world!");
    ... ''')
    'var Greeter = (function () {\n    function Greeter(greeting) {\n        this.greeting = greeting;\n    }\n    Greeter.prototype.greet = function () {\n        return "<h1>" + this.greeting + "</h1>";\n    };\n    return Greeter;\n})();\n;\nvar greeter = new Greeter("Hello, world!");\n'

Atualmente, o compilador tem opções incorporadas e não aceita opções adicionais,

O compilador TypeScript baseado em DukPY também fornece um filtro WebAssets (
http://webassets.readthedocs.org/en/latest/) para compilar automaticamente 
o código TypeScript no pipeline de ativos. Você registra este filtro como 
`` typescript`` dentro do WebAssets usando:

.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import TypeScript

    register_filter(TypeScript)

O que torna o filtro disponível com o nome ``typescript``.

**NOTA:** Ao usar o compilador TypeScript para o código que precisa ser executado
no navegador, certifique-se de adicionar a dependência 
https://cdnjs.cloudflare.com/ajax/libs/systemjs/0.19.24/system.js. 
Como as declarações `` import`` são resolvidas usando o SystemJS.


EcmaScript6 BabelJS Transpiler
------------------------------

Para compilar o código ES6 para o ES5 para uso diário, você pode usar
`` dukpy.babel_compile``:


.. code:: python

    >>> import dukpy
    >>> dukpy.babel_compile('''
    ... class Point {
    ...     constructor(x, y) {
    ...             this.x = x;
    ...         this.y = y;
    ...         }
    ...         toString() {
    ...             return '(' + this.x + ', ' + this.y + ')';
    ...         }
    ... }
    ... ''')
    '"use strict";\n\nvar _prototypeProperties = function (child, staticProps, instanceProps) { if (staticProps) Object.defineProperties(child, staticProps); if (instanceProps) Object.defineProperties(child.prototype, instanceProps); };\n\nvar _classCallCheck = function (instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } };\n\nvar Point = (function () {\n    function Point(x, y) {\n        _classCallCheck(this, Point);\n\n        this.x = x;\n        this.y = y;\n    }\n\n    _prototypeProperties(Point, null, {\n        toString: {\n            value: function toString() {\n                return "(" + this.x + ", " + this.y + ")";\n            },\n            writable: true,\n            configurable: true\n        }\n    });\n\n    return Point;\n})();\n'

Você pode passar `opções`__ para o compilador BabelJS como palavras-chave 
na chamada para ``babel_compile()``.

__ http://babeljs.io/docs/usage/options/

O compilador BabelJS baseado em DukPY também fornece um filtro WebAssets (
http://webassets.readthedocs.org/en/latest/) para compilar automaticamente 
o código ES6 em seu pipeline de ativos. Você registra este filtro como 
`` babeljs`` dentro de WebAssets usando:


.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import BabelJS

    register_filter(BabelJS)

O que torna o filtro disponível com o nome `` babeljs``. 
A única opção de filtro suportado atualmente é `BABEL_MODULES_LOADER` com o valor
``systemjs`` ou``umd`` para especificar que o código compilado deve usar SystemJS 
ou UMD ao invés do CommonJS para módulos.

**NOTA:** Ao usar o compilador BabelJS para código que precisa ser executado 
no navegador, certifique-se de adicionar a dependência 
https://cdnjs.cloudflare.com/ajax/libs/babel polyfill / 6.13.0 / polyfill.min.js.

JSX para Reagir ao Transpilar
------------------------

O DukPy fornece um compilador embutido do JSX para o React, que está disponível como 
`` dukpy.jsx_compile``:

.. code:: python

    >>> import dukpy
    >>> dukpy.jsx_compile('var react_hello = <h1>Hello, world!</h1>;')
    u'"use strict";\n\nvar react_hello = React.createElement(\n  "h1",\n  null,\n  "Hello, world!"\n);'

O compilador JSX baseado em DukPY também fornece um filtro WebAssets (
http://webassets.readthedocs.org/en/latest/) para compilar automaticamente 
o código JSX + ES6 no pipeline de recursos. Você registra este filtro como 
`` babeljsx`` dentro de WebAssets usando:


.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import BabelJSX

    register_filter(BabelJSX)

O que torna o filtro disponível com o nome `` babeljsx``. 
Este filtro suporta as mesmas opções que o babel.


Less Transpiling
----------------

O DukPy fornece uma distribuição embutida do compilador Less disponível 
através do `dukpy.less_compile`:


.. code:: python

    >>> import dukpy
    >>> dukpy.less_compile('.class { width: (1 + 1) }')
    '.class {\n  width: 2;\n}\n'


O compilador LESS baseado em DukPY também fornece um filtro WebAssets (
http://webassets.readthedocs.org/en/latest/) para compilar automaticamente 
o código LESS no pipeline de ativos. Você registra este filtro como 
`` lessc`` dentro do WebAssets usando:


.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import CompileLess

    register_filter(CompileLess)

O que torna o filtro disponível com o nome ``lessc``.


Usando o Interpretador JavaScript 
--------------------------------

Usar o dukpy é tão simples quanto chamar a função `` dukpy.evaljs`` 
com o código javascript:


.. code:: python

    >>> import dukpy
    >>> dukpy.evaljs("var o = {'value': 5}; o['value'] += 3; o")
    {'value': 8}


A função `` evaljs`` executa o javascript e retorna o valor 
resultante na medida em que é possível codificá-lo em JSON.

Se a execução falhar, uma exceção `` dukpy.JSRuntimeError`` 
é levantada com o motivo da falha.


Passando Argumentos
~~~~~~~~~~~~~~~~~

Qualquer argumento passado para `` evaljs`` está disponível em JavaScript 
dentro do objeto `` dukpy`` em javascript. Deve ser possível codificar 
os argumentos usando JSON para que eles estejam disponíveis em Javascript:


.. code:: python

    >>> import dukpy
    >>>
    >>> def sum3(value):
    ...     return dukpy.evaljs("dukpy['value'] + 3", value=value)
    ...
    >>> sum3(7)
    10

Executando Múltiplos Scripts
~~~~~~~~~~~~~~~~~~~~~~~~

A função `` evaljs`` suporta o fornecimento de múltiplos códigos fontes para 
serem executados no mesmo contexto.

Múltiplos scripts podem ser passados em uma lista ou tupla:

.. code:: python

    >>> import dukpy
    >>> dukpy.evaljs(["var o = {'value': 5}",
    ...               "o['value'] += 3",
    ...               "o"])
    {'value': 8}

Isso é útil quando seu código requer dependências para funcionar, 
pois você pode carregar a dependência e, em seguida, seu código.

É assim que o compilador de coffeescript é implementado pelo próprio DukPy:


.. code:: python

    def coffee_compile(source):
        with open(COFFEE_COMPILER, 'r') as coffeescript_js:
            return evaljs((coffeescript_js.read(), 'CoffeeScript.compile(dukpy.coffeecode)'),
                          coffeecode=source)

Usando um Interpretador JavaScript persistente
-----------------------------------------

A função `` evaljs`` cria um novo intérprete em cada chamada, 
isto é geralmente conveniente e evita erros devido a variáveis globais de sujeira 
ou status de execução inesperado.

Em alguns casos, você pode querer executar um código que tenha um bootstrap lento, portanto, 
é conveniente reutilizar o mesmo interpretador entre duas chamadas diferentes, 
de modo que o custo de bootstrap já tenha sido pago durante a primeira execução.

Isto pode ser conseguido usando o objeto `` dukpy.JSInterpreter``.

Criar um `` dukpy.JSInterpreter`` permite avaliar o código dentro daquele interpretador 
e várias chamadas `` eval`` irão compartilhar o mesmo interpretador e status global:



.. code:: python

    >>> import dukpy
    >>> interpreter = dukpy.JSInterpreter()
    >>> interpreter.evaljs("var o = {'value': 5}; o")
    {u'value': 5}
    >>> interpreter.evaljs("o.value += 1; o")
    {u'value': 6}

Carregando módulos com require
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ao usar o objeto `` dukpy.JSInterpreter`` é possível usar 
a instrução `` require ('modulename') `` para carregar um módulo dentro do javascript.

Os módulos são procurados em todos os diretórios registrados com 
`` dukpy.JSInterpreter.loader.register_path``:


.. code:: python

    >>> import dukpy
    >>> jsi = dukpy.JSInterpreter()
    >>> jsi.loader.register_path('./js_modules')
    >>> jsi.evaljs("isEmpty = require('fbjs/lib/isEmpty'); isEmpty([1])")
    False

Instalando pacotes do npmjs.org
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ao usar o interpretador javascript persistente, também é possível instalar pacotes 
do * npmjs.org * através da função `` dukpy.install_jspackage``:


.. code:: python

    >>> import dukpy
    >>> jsi = dukpy.JSInterpreter()
    >>> dukpy.install_jspackage('promise', None, './js_modules')
    Packages going to be installed: promise->7.1.1, asap->2.0.3
    Fetching https://registry.npmjs.org/promise/-/promise-7.1.1.tgz..........................
    Fetching https://registry.npmjs.org/asap/-/asap-2.0.3.tgz............
    Installing promise in ./js_modules Done!

A mesma funcionalidade também é fornecida pelo comando shell `` dukpy-install`` ::


    $ dukpy-install -d ./js_modules promise
    Packages going to be installed: promise->7.1.1, asap->2.0.3
    Fetching https://registry.npmjs.org/promise/-/promise-7.1.1.tgz..........................
    Fetching https://registry.npmjs.org/asap/-/asap-2.0.3.tgz............
    Installing promise in ./js_modules Done!

Por favor note que atualmente o `install_jspackage` não é capaz de resolver dependências 
conflitantes.


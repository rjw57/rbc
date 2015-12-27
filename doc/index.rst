rbc: Rich's B compiler
======================

.. |---| unicode:: U+02014 .. em dash
   :trim:

This document describes my attempt at writing a compiler for the `B programming
language`_ for fun over the Christmas vacation 2015.  B is a language developed
around the early 70s which is a direct predecessor of C. The compiler is
written in Python and uses LLVM for cross-platform native code generation.

It is intended to serve as a good introductory example of writing a compiler
targeting LLVM. After all, I wrote it to learn just that.

.. _B programming language: https://en.wikipedia.org/wiki/B_(programming_language)

Usage Summary
-------------

See the :download:`README.rst <../README.rst>` file for installation
instructions. The compiler provides a single command: ``rbc``.

Given the following program:

.. literalinclude:: example/helloworld.b

The ``rbc`` compiler can compile it into a native executable:

.. code:: console

   $ rbc -o hw helloworld.b
   $ ./hw
   Hello, world!

It can emit ELF object files:

.. code:: console

   $ rbc -c helloworld.b
   $ file helloworld.o
   helloworld.o: ELF 64-bit LSB relocatable, x86-64, version 1
   (GNU/Linux), not stripped
   $ nm helloworld.o
   0000000000000000 T b.main
                    U b.putstr

It can emit native assembly:

.. code:: console

   $ rbc -s helloworld.s
   $ cat helloworld.s
           ...
   b.main:
           .cfi_startproc
           pushq   %rax
   .Ltmp0:
           .cfi_def_cfa_offset 16
           movl    $.Lb.__str.0, %edi
           shrq    $3, %rdi
           callq   b.putstr
           xorl    %eax, %eax
           popq    %rdx
           retq
   .Ltmp1:
           .size   b.main, .Ltmp1-b.main
           .cfi_endproc
           ...

Much like the clang compiler, the ``--emit-llvm`` flag may be specified to emit
LLVM bitcode and LLVM IR assembly in place of native objects and native
assembly.

Overview
--------

This document starts with an introduction to the project, its scope and the aims
I had when starting. The high-level Python interface to the compiler is
then discussed. An overview of the tooling used to generate the parser and a
discussion of the abstract syntax tree follows. Code generation via LLVM is then
discussed. Finally an API reference is provided.

Introduction
------------

Over Christmas 2015 I thought that it would be a great little project to write a
compiler. I'd initially thought about writing a tiny little C compiler. Despite
its widespread use, C is still a small language and it's feasible for a single
person to write a reasonably useful C compiler. However, it's still a little
large for a Christmas project. Also, over the years C has developed a handy set
of corner-cases and gotchas which arose as part of the standardisation effort.
Spending days scouring the standard to iron out pedantic wrinkles didn't appeal.
Additionally, my system has at least three C compilers already installed. It
didn't need an extra one.

So, C was rejected as being slightly too big and slightly too subtle. However, C
was not developed in a vacuum. It arose from a family of languages primarily
developed by Ken Thompson and Dennis Ritchie at Bell Labs in the 70s.  One of
these "proto-C" languages was the aptly named "B" language. As Ritchie states in
his excellent article "`The Development of the C Language`_":

   Challenged by McIlroy's feat in reproducing TMG, Thompson decided that Unix
   |---| possibly it had not even been named yet |---| needed a system
   programming language. After a rapidly scuttled attempt at Fortran, he created
   instead a language of his own, which he called B. B can be thought of as C
   without types; more accurately, it is BCPL squeezed into 8K bytes of memory
   and filtered through Thompson's brain.

.. _The Development of the C Language: https://www.bell-labs.com/usr/dmr/www/chist.html

B is therefore historically interesting, C-like, practical and, most importantly
small. It's also a "real language" which was used in anger and hence would be
useful as a means to keep me honest. By implementing an existing language I
wouldn't fall into the trap of accidentally designing a language which made the
compiler trivially easy to write.

.. sidebar:: The final boss?

   Up until recently I would have said that writing a compiler for any
   non-trivial language is a sort of "final boss" for CompSci.  Compilers touch
   nearly all parts of the CompSci "stack" all the way from the theoretical
   world of formal grammars and type systems through data structures down to the
   ruthlessly practical level of machine code and systems design.

   Nowadays I'd say that web browsers have taken over from compilers as the
   final boss since a web browser contains a JavaScript compiler as a subset,
   needs to render graphics and, in the case of WebGL, interact with the GPU.
   Nonetheless, a compiler is still a very good and, importantly, an achievable)
   learning exercise.

Scope and Aims
--------------

I started out with a few goals and non-goals in mind. Firstly, I wanted the
compiler to work with the rest of the compiler ecosystem; I wanted it to
generate real ELF objects which could be linked with the system linker. It was
important to me that an actual runnable binary be produced rather than some form
of hybrid JIT/interpreter.

Writing the compiler in a high-level language appealed to me. I like the idea
that a language `from the early 70s`_ could be compiled with a compiler written
in a language so far down the evolutionary chain that it could barely have been
conceived when B was being used. My high-level language of choice is Python. I'm
familiar with it and I find writing small projects in Python calming and
enjoyable. Python also lends itself to readable code and there's a wide variety
of existing libraries which I could leverage to get the job done.

.. _from the early 70s: https://www.bell-labs.com/usr/dmr/www/kbman.html

Today, `LLVM`_ is really the only choice for getting a compiler up and running
quickly assuming you've not got any compiler infrastructure to start from. (When
Robert Griesemer, Rob Pike and Ken Thompson later started the `Go language`_
project they famously rejected LLVM but then they had the entire `Plan 9`_
compiler toolchain to work from.) There are official Python bindings for LLVM
but they are not terribly easy to install automatically and I wanted a compiler
which was a simple ``pip install`` away. This is mostly because I'm lazy and
wanted to make use of the `tox`_ system to automatically install and test the
compiler in a virtualenv.

.. _LLVM: http://llvm.org/

.. _Go language: https://golang.org/

.. _Plan 9: http://plan9.bell-labs.com/plan9/

.. _tox: https://tox.readthedocs.org/

The `llvmlite`_ bindings looked suitable. Although llvmlite is geared more to
writing JITs for domain specific languages, a look through the documentation
revealed it probably exposed enough features for my needs.

.. _llvmlite: http://llvmlite.pydata.org/

Despite wanting the compiler to be useful and to generate reasonably efficient
output, I didn't care too much about the speed or efficiency of the compiler
*per se*. I wanted the compiler to be small, understandable and readable. If
that made it ten times slower, I didn't mind. After all, I wasn't writing a
production B compiler, I was writing code for fun.

I was also unconcerned with the quality of diagnostic messages. Getting a
compiler to produce good error messages is hard and I was more concerned with
generating correct output for correct input. The compiler assumes a sufficiently
clever user.

The B programming language
--------------------------

This section discusses the history of the B language and will provide some
example code. It will not attempt to be a full description of the language.

Writing this compiler has really made me appreciate the position B occupies with
respect to the history of C. The restrictions of the PDP-7 environment it was
created in meant that it clearly demonstrates the asceticism of C but has one
foot firmly in the BCPL camp. It's also the initial appearance of a few familiar
friends: the pre- and post-operators ``++`` and ``--`` along with the first
example of a "Hello, world!" program in an accompanying tutorial.

Following that tradition, here is a possible "Hello, world!" in B:

.. literalinclude:: example/helloworld.b

This may be compiled via the ``rbc`` tool and directly executed:

.. command-output:: rbc example/helloworld.b && ./a.out
   :shell:

A few C-like things should be immediately obvious. Comments are surrounded by
``/*`` and ``*/``. (This originated in PL/I.) The entry point is a ``main``
function. There are curly braces wrapping statements. The statements end with a
semicolon. Function calls and string constants look very familiar. Less
obvious, but similar to C, the string constant evaluates to the address of the
first character of the string and consists of the character bytes packed in
memory terminated by a special byte.

There are also a few oddities. Instead of the now near-universal
"backslash-letter" form of escape sequence, B used "asterisk-letter". That being
said, ``*n`` means "newline" just as ``\n`` does today. The string constant is
terminated by an ASCII EOT (end of transmission) byte rather than a NUL. There
are also no function declarations. How, for example, does B know that ``putstr``
is a function?

The answer is both simple and surprising. If you use a value like a function, B
treats it as a function pointer. If you use it like an array, B treats it as
such. There is no type system to speak of in B. All values are of type "word".
If a value is dereferenced, it is assumed to have been a pointer.

In principle this should make B a very simple language to implement. There are
no complex type promotion and punning rules. This simplicity did lead to a
slightly annoying implementation problem which I'll discuss later.

B supports array types and character constants which look spookily familiar::

   main() {
      auto i;
      extrn putchar, chars;
      i = 0;
      while(i < 8) {
         putchar(chars[i++]);
      }
   }
   chars [] 'L', 'o', ' ', 'w', 'r', 'l', 'd', '*n';

A far fuller introduction is available in "`A Tutorial Introduction to the
Language B`_" written by Brian Kernighan.

.. _A Tutorial Introduction to the Language B: https://www.bell-labs.com/usr/dmr/www/btut.html

The actual number of bits in a B word has always been machine dependent.
Generally it was assumed to be at least 16 bits or 2 bytes. The dialect of B
supported by rbc considers a word to be the smallest integer which can store a
pointer. Hence, a word is 8 bytes long on a 64-bit architecture or 4 bytes on a
32-bit one. The number of bytes in the word can be retrieved by way of a special
builtin variable::

   main() {
      extrn putnumb;
      putnumb(__bytes_per_word); /* Usually prints 4 or 8. */
   }

This builtin may give the illusion of portability but I suspect that the effort
required to write maximally portable B code is probably not worth the results.

Structure of the rbc compiler
-----------------------------

This section describes the high-level structure of the rbc compiler in terms of
data flow from source code to object code and executable.

In common with most compilers, rbc starts by transforming a file containing B
source code into a tree data structure known as the parse tree. The parse tree
is then transformed into an Abstract Syntax Tree (AST). This is a tree structure
which represents the B program in a form convenient for generating code. Finally
the AST is transformed into a LLVM intermediate representation (IR) assembly
file.  The process is summarised below:

.. graphviz:: fig/source_to_ir.dot

In this figure, rectangular nodes represent the data structures or files on disk
and the plain text nodes represent software modules which transform one data
structure into another. We will discuss each rbc module below.

After the LLVM IR has been generated, rbc makes use of the existing LLVM
infrastructure and platform linker to generate an executable file. At this stage
the ``libb.o`` object file containing the B standard library is also linked in:

.. graphviz:: fig/llvm_to_exe.dot

Notice that the standard library is written in both C *and* B. This is to allow
use of the portable standard C library for I/O.

Using the compiler via the Python API
-------------------------------------

.. todo:: Complete section

Implementation
--------------

Parsing and semantics
'''''''''''''''''''''

We make use of the grako_ parser tool for Python to generate the parser. It's
simple to use and provides a useful abstraction between the structure of the
parse tree and the structure of the AST.

The input to grako is the :download:`B.ebnf <../B.ebnf>` file. This file
specifies the grammar of the B language in EBNF_ form as a `Parsing Expression
Grammar`_ (PEG). Grako then compiles the EBNF grammar into the parser module
source file :download:`parser.py <../rbc/parser.py>`.

.. _grako: https://pypi.python.org/pypi/grako

.. _EBNF: https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_Form

.. _Parsing Expression Grammar: https://en.wikipedia.org/wiki/Parsing_expression_grammar

The parser is encapsulated within the :py:class:`rbc.parser.BParser` class which
provides a single public method: :py:meth:`.parse`.

Grako abstracts the parse tree/abstract syntax tree distinction by way of a
*semantics* object. For each rule of the EBNF grammar, a corresponding method is
called on the semantics object. For example, the initial definition of
:py:class:`rbc.semantics.BSemantics` is as follows:

.. code:: python

   class BSemantics(object):
       def __init__(self, make_node):
           self._node = make_node

       def program(self, definitions):
           return self._node('Program', definitions=definitions)

       def simpledef(self, ast):
           return self._node('SimpleDefinition',
                             name=ast.name, init=ast.init)

The first part of the (simplified) EBNF grammar is as follows::

   program = @:{ definition } $ ;

   definition = simpledef | vectordef | functiondef ;

   simpledef = name:name init:[ival] ';' ;

   ival = numericexpr | characterexpr | stringexpr ;

   (* ... etc *)

Each method in :py:class:`.BSemantics` gets passed the parse tree node
(confusingly referred to as ``ast``). In the case of ``program``, the ``@:`` tag
indicates that the rule be passed a sequence of each parsed ``definition``.
The ``simpledef`` rule names its constituent rules and they are passed in a
dict-like object which also exposes its keys as attributes.

At construction time, we pass the object a callable, ``make_node``, which is
used to construct the actual AST node. The actual AST node type is opaque to the
semantics allowing the creation of multiple code generators or, for debugging,
an AST visualisation.

For example, the :py:mod:`rbc.dumpast` module contains a class,
:py:class:`GraphvizAST` which may be used to visualise the AST via graphviz:

.. code:: python

   import sys
   from rbc.dumpast import GraphvizAST
   from rbc.parser import BParser
   from rbc.semantics import BSemantics

   # Create a graphviz AST implementation
   ast = GraphvizAST()

   # Load some source code from the file specified as the first CLI
   # argument.
   with open(sys.argv[1]) as f:
      source = f.read()

   # Parse the source
   BParser().parse(source, 'program',
                   semantics=BSemantics(ast.make_node))

   # Write the AST to standard output
   ast.emit(sys.stdout)

Passing the following program:

.. include:: fig/graphvizex.b
   :literal:

Results in the following graph:

.. graphviz:: fig/graphvizex.ast.dot

Code generation
'''''''''''''''

The LLVM code for the program is emitted after the program has been fully
parsed. This is required because B functions may refer to functions and external
variables which have not yet been defined in the program.

LLVM code is emitted within an "emit context". (See
:py:class:`rbc.codegen.EmitContext`.) This is some mutable state which is used
to keep important information on the program and the current state of the LLVM
code emission.

Symbol naming
'''''''''''''

B allows for global externally visible symbols such as functions. To avoid
clashes with the C world, we mangle the symbol names. By default the B world
can't see C and vice versa. This is done by prefixing all B symbols with "b."
which renders them invalid as C identifiers. The function
:py:func:`.mangle_symbol_name` is used as a central place to record this
convention.

Addresses and pointers and words, oh my!
''''''''''''''''''''''''''''''''''''''''

Although B lacks what would today be called a type system (every object is
of type "word") there is an implicit one in that addresses are assumed to
be word oriented and thus "address" + "word" should really be "address" +
(word size * "word") in a byte-oriented architecture. We need to tackle
this since ``a[b]`` is syntactic sugar for ``*(a + b)`` and we don't know at
emit time which of a and/or b are pointers.  This is further complicated by the
fact that *neither* of ``a`` or ``b`` *need* be pointers, ``1[2]`` is a valid
vector expression in B, albeit one likely to lead to an invalid memory access.

The most straight-forward approach is to have address values be stored
word-oriented which requires that the alignment of the target be suitable. This
also necessitates the use of constructor functions and wrappers to shuffle
between "addresses" and pointers used by LLVM.

lvalues and rvalues
'''''''''''''''''''

B divides values into two categories: *lvalue* and *rvalue*. The essential
difference is that an lvalue represents the address in memory of some other
value. Thus each lvalue has an associated rvalue (the value pointed to by the
address) but each rvalue does not have an associated lvalue. If an rvalue *does*
have some address associated with it the address may be obtained via the ``&``
or "reference" operator. This address is itself an rvalue. An rvalue may not be
referenced. Both lvalues and rvalues may be "dereferenced" via the ``*``
operator to yield an lvalue.

Scopes
''''''

Scopes associate names with lvalues. The addresses associated with lvalues never
change. "Assigning" to a variable involves writing a new value at the associated
address. Variables are simply the lvalues in scopes retrieved by name but the
name is only looked up at emit()-time. This is to allow forward-references to
in-scope but yet-to-be-declared variables such as global definitions.

Scopes are implemented as dict-like objects with string keys and LValue values.

Names
'''''

A fundamental token type in B is the *name*. According to the reference manual:

   The characters ``A`` through ``Z``, ``a`` through ``z``, ``_``, ``.``, and
   backspace are alphabetic characters and may be used in names. The characters
   ``0`` through ``9`` are digits and may be used in constants or names;
   however, a name may not begin with a digit.

The grako tool allows regular expressions to be used in parsers. We can express
the rule above via the following EBNF::

   name = head:ALPHA tail:{ ALPHA | NUMERIC } ;

   ALPHA = /[A-Za-z_\.\b]/ ;

   NUMERIC = /[0-9]/ ;

In grako's dialect of EBNF, rules with capitalised names do not skip whitespace
whereas other rules do. The corresponding :py:class:`.BSemantics` method is:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.name
   :dedent: 4

String, character and numeric expressions
'''''''''''''''''''''''''''''''''''''''''

In B, string, character and numeric expressions are "constant" in that their
values are known as compile time. Strings and numeric expressions are very much
like their C counterparts. Character constants are unlike C in that they can
contain more than one character. The ASCII code for each character in a
character constant is packed into a single right aligned, zero padded machine
word. Thus on a 32-bit machine there can in fact be up to 4 charachers in a
single character constant.

The grammar is straightforward::

   numericexpr = { NUMERIC }+ ;

   characterexpr = "'" @:{ CHARACTERCONSTCHAR } "'" ;

   stringexpr = '"' @:{ STRINGCONSTCHAR } '"' ;

   CHARACTERCONSTCHAR = /([^'\*])|(\*.)/ ;

   STRINGCONSTCHAR = /([^"\*])|(\*.)/ ;

And, similarly, the semantic method for ``numericexpr`` is fairly simple:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.numericexpr
   :dedent: 4

The corresponding :py:class:`.BSemantics` methods are a little more subtle in
that both character and string constants may contain escape characters. For
example the sequence ``*n`` expands to ASCII LF, or character code 10. To help
with this expansion, we define a helper function:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: _expand_escapes

The semantic method for ``characterexpr`` makes use of this helper:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.characterexpr
   :dedent: 4

The semantic method for ``stringexpr`` stores the contents of the string as a
``bytes`` object since the encoding is specified to be ASCII.

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.stringexpr
   :dedent: 4

We can now parse a file with some simple external variable definitions and see
the resulting AST:

.. literalinclude:: fig/simpledefs.b

.. graphviz:: fig/simpledefs.ast.dot

Vector externals
''''''''''''''''

Unlike a simple external definition, a vector definition can take both a maximum
index and a list of initialisers. Note that the vector is defined by the maximum
index and is 0-based and so the external variable definition

.. code::

   myvec [5]

actually defines a vector of length *six* elements. I.e., indices 0 through 5.
The grammar is as follows::

   vectordef = name:name '[' [ maxidx:constantexpr ] ']'
               [ ivals:ivallist ] ';' ;

   ivallist = @+:ival { ',' @+:ival } ;

   constantexpr = numericexpr | characterexpr ;

The corresponding semantic method is:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.vectordef
   :dedent: 4

Parsing the following file:

.. literalinclude:: fig/vectordef.b

Results in:

.. graphviz:: fig/vectordef.ast.dot

Functions
'''''''''

A function is an external definition which has a list of arguments and a body.
The grammar is::

   functiondef = name:name '(' [ args:namelist ] ')'
                 body:statement ;

   namelist = @+:name { ',' @+:name } ;

   statement = labelstatement | gotostatement | switchstatement
             | casestatement | breakstatement | autostatement
             | extrnstatement | compoundstatement | ifstatement
             | whilestatement | returnstatement | exprstatement
             | nullstatement ;

   (* TODO: define most statement types above *)

   compoundstatement = '{' ~ @:{ statement ~ } '}' ;

We'll define the remaining statement types below. For the moment, we need only
define a compound statement:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.compoundstatement
   :dedent: 4

This provides enough infrastructure to define the ``functiondef`` semantics:

.. literalinclude:: ../rbc/semantics.py
   :pyobject: BSemantics.functiondef
   :dedent: 4

We can now parse the following program:

.. literalinclude:: fig/functiondef.b

.. graphviz:: fig/functiondef.ast.dot

Null statements
'''''''''''''''

"Extrn" statements
''''''''''''''''''

"Auto" statements
'''''''''''''''''

Expressions
'''''''''''

Return statements
'''''''''''''''''

Compound statements
'''''''''''''''''''

Break statements
''''''''''''''''

If statements
'''''''''''''

While statements
''''''''''''''''

Goto and label statements
'''''''''''''''''''''''''

Switch and case statements
''''''''''''''''''''''''''

Reference
---------

Errors
''''''

.. automodule:: rbc.exception
   :members:

Semantics
'''''''''

.. automodule:: rbc.semantics
   :members:

Compiler
''''''''

.. automodule:: rbc.compiler
   :members:

Code generation
'''''''''''''''

.. automodule:: rbc.codegen
   :members:

.. autoclass:: rbc.codegen.astnode.ASTNode
   :members:

.. automodule:: rbc.codegen.context
   :members:

Rich's B Compiler
=================

[![Build Status](https://travis-ci.org/rjw57/rbc.svg?branch=master)](https://travis-ci.org/rjw57/rbc)

This repository contains my experimental B compiler written as a Christmas
vacation project 2015.

Installation and getting started
--------------------------------

The llvmlite bindings require (as of writing) LLVM version 3.6. Make sure to set
the LLVM_CONFIG environment variable appropriately.

On Debian/Ubuntu-like Linuxes::

   $ sudo apt install llvm-dev-3.6
   $ export LLVM_CONFIG=llvm-config-3.6

On OSX::

   $ brew install llvm
   $ export LLVM_CONFIG=/usr/local/opt/llvm/bin/llvm-config

Then install via pip::

   $ cd /path/to/rbc
   $ pip install -e .

B code can then be compiled via the ``rbc`` tool::

   $ echo 'main(){ extrn putstr; putstr("hello!*n"); }' >greet.b
   $ rbc -o greet greet.b
   $ ./greet
   hello!

Notes
-----

The C-library "putchar" function is very similar to B's.

LLVM can optimise a recursive factorial function into a loop.


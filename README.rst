Rich's B Compiler
=================

.. image:: https://travis-ci.org/rjw57/rbc.svg?branch=master
    :target: https://travis-ci.org/rjw57/rbc

This repository contains my experimental B compiler written as a Christmas
vacation project 2015.

Installation and getting started
--------------------------------

The llvmlite bindings require (as of writing) LLVM version 3.6. Make sure to set
the LLVM_CONFIG environment variable appropriately.

On Debian/Ubuntu-like Linuxes::

   $ sudo apt install libedit-dev llvm-dev-3.6
   $ export LLVM_CONFIG=llvm-config-3.6

On OSX::

   $ brew install llvm
   $ export LLVM_CONFIG=/usr/local/opt/llvm/bin/llvm-config

Then install via pip::

   $ pip install git+https://github.com/rjw57/rbc

Developers may manually clone the repository if they want::

   $ git clone git://github.com/rjw57/rbc
   $ cd /path/to/rbc; pip install -e .

B code can then be compiled via the ``rbc`` tool::

   $ echo 'main(){ extrn putstr; putstr("hello!*n"); }' >greet.b
   $ rbc -o greet greet.b
   $ ./greet
   hello!

Examples
--------

Calculating *e*
'''''''''''''''

The following example is taken from a B tutorial::

   /* calce.b:
      The following program will calculate the constant e-2 to about
      4000 decimal digits, and print it 50 characters to the line in
      groups of 5 characters.  The method is simple output conversion
      of the expansion
        1/2! + 1/3! + ... = .111....
      where the bases of the digits are 2, 3, 4, . . . */

   main() {
      extrn putchar, n, v;
      auto i, c, col, a;

      i = col = 0;
      while(i<n)
         v[i++] = 1;
      while(col<2*n) {
         a = n+1 ;
         c = i = 0;
         while (i<n) {
            c =+ v[i] *10;
            v[i++]  = c%a;
            c =/ a--;
         }

         putchar(c+'0');
         if(!(++col%5))
            putchar(col%50?' ': '*n');
      }
      putchar('*n*n');
   }

   v[2000];
   n 2000;

Save this code to ``calce.b``. Compile and run::

   $ rbc calce.b && ./a.out | head
   71828 18284 59045 23536 02874 71352 66249 77572 47093 69995
   95749 66967 62772 40766 30353 54759 45713 82178 52516 64274
   27466 39193 20030 59921 81741 35966 29043 57290 03342 95260
   59563 07381 32328 62794 34907 63233 82988 07531 95251 01901
   15738 34187 93070 21540 89149 93488 41675 09244 76146 06680
   82264 80016 84774 11853 74234 54424 37107 53907 77449 92069
   55170 27618 38606 26133 13845 83000 75204 49338 26560 29760
   67371 13200 70932 87091 27443 74704 72306 96977 20931 01416
   92836 81902 55151 08657 46377 21112 52389 78442 50569 53696
   77078 54499 69967 94686 44549 05987 93163 68892 30098 79312

Factorial
'''''''''

The following example shows how the compiler may optimise recursion::

   $ echo 'fact(n) return (n==0?1:n*fact(n-1));' >fact.b
   $ rbc --emit-llvm -s fact.b
   $ cat fact.ll
   ; ModuleID = 'fact.b'
   target datalayout = "e-m:e-i64:64-f80:128-n8:16:32:64-S128"
   target triple = "x86_64-pc-linux-gnu"

   ; Function Attrs: nounwind readnone
   define i64 @b.fact(i64 %n) #0 {
   entry:
     %.71 = icmp eq i64 %n, 0
     br i1 %.71, label %entry.endif, label %entry.else.preheader

   entry.else.preheader:                             ; preds = %entry
     br label %entry.else

   entry.else:                                       ; preds = %entry.else.preheader, %entry.else
     %n.tr3 = phi i64 [ %.20, %entry.else ], [ %n, %entry.else.preheader ]
     %accumulator.tr2 = phi i64 [ %.22, %entry.else ], [ 1, %entry.else.preheader ]
     %.20 = add i64 %n.tr3, -1
     %.22 = mul i64 %n.tr3, %accumulator.tr2
     %.7 = icmp eq i64 %.20, 0
     br i1 %.7, label %entry.endif.loopexit, label %entry.else

   entry.endif.loopexit:                             ; preds = %entry.else
     %.22.lcssa = phi i64 [ %.22, %entry.else ]
     br label %entry.endif

   entry.endif:                                      ; preds = %entry.endif.loopexit, %entry
     %accumulator.tr.lcssa = phi i64 [ 1, %entry ], [ %.22.lcssa, %entry.endif.loopexit ]
     ret i64 %accumulator.tr.lcssa
   }

   attributes #0 = { nounwind readnone }

Notice that the recursive ``fact`` function has been optimised into the
equivalent looping version.


"""
LLVM code generation.

"""
from __future__ import print_function

import contextlib
import functools

import future.moves.collections as collections
from future.builtins import bytes
from llvmlite import ir

import rbc.exception as exc

# HACK: make sure all the AST node types are imported and registered
from . import astnode, expression, external, statement
from . import context

# Constructing AST Nodes
# ======================
#
# AST nodes may be constructed via the make_node function. The advantage of the
# make_node function is one doesn't need to explicitly import all the AST node
# classes.

def make_node(type_name, **kwargs):
    """Construct an AST node given the type name and a set of keyword arguments.

    Returns:
        An :py:class:`.astnode.ASTNode` object.

    Raises:
        InternalCompilerError if type_name does not correspond to a known node.

    """

    try:
        return astnode.make_node(type_name, **kwargs)
    except KeyError:
        raise exc.InternalCompilerError(
            'Unknown AST node: {}'.format(type_name))

# Programs
# ========

@astnode.ast_node
class Program(astnode.ASTNode):
    """A program is the root-level AST node. It provides a single method,
    :py:meth:`.emit`, which returns the LLVM module assembly as a string.

    """
    def emit(self, target, machine):
        """Take an llvm Target and TargetMachine instance representing the
        ultimate target for the emitted code.

        Returns:
            A stirng containing the LLVM module assembly code.

        """
        # Create a new emit context for the program
        ctx = context.EmitContext(target, machine)

        with ctx.emitting_code():
            # Declare all top-level definitions
            for defn in self.definitions:
                defn.declare(ctx)

            # Emit global definitions
            for emittable in self.definitions:
                emittable.emit(ctx)

        return str(ctx.module)

"""
Abstract syntax tree nodes capable of emitting LLVM instructions.

"""
import functools

import rbc.exception as exc

# Constructing AST Nodes
# ======================
#
# AST nodes may be constructed directly via the class object or indirectly via
# the make_node function. The advantage of the make_node function is one doesn't
# need to explicitly import all the AST node class names.

# A map of node names -> node classes used by make_node.
_NODE_CLASSES = {}

def make_node(type_name, **kwargs):
    """Construct an AST node given the type name and a set of keyword arguments.

    Returns:
        An ASTNode object.

    Raises:
        KeyError if type_name does not correspond to a known node.

    """
    return _NODE_CLASSES[type_name](**kwargs)

def ast_node(cls):
    """Class decorator which registers the AST node in the _NODE_CLASSES map."""
    _NODE_CLASSES[cls.__name__] = cls
    return cls

# AST Nodes
# =========
#
# AST nodes fundamentally store key/value associations much like dicts. Unlike
# dicts AST nodes don't support iterating over the values and instead expose the
# values directly as attributes.

class ASTNode(object):
    """An AST node with parameters directly accessible as attributes."""
    def __init__(self, **kwargs):
        # Set attributes on ourself directly from the keyword args.
        for k, v in kwargs.items():
            setattr(self, k, v)

# Emittable nodes
# ===============
#
# Most AST nodes are "emittables" in that they have an emit() method which takes
# the current context and returns an llvm Value corresponding to that node. Some
# nodes do not have a corresponding llvm Value and so return None from emit().
# The Program node returns the entire LLVM module assembly as a string value.

def needs_builder(emit):
    """A decorator for emit() methods which make use of the context's builder
    attribute. If the builder attribute is None, an InternalCompilerError is
    raised.

    """
    @functools.wraps(emit)
    def _wrapped_emit(self, context):
        if context.builder is None:
            raise exc.InternalCompilerError('AST node requires builder.')
        return emit(self, context)
    return _wrapped_emit

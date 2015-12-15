"""
Custom exception subclasses.

"""

class SemanticError(RuntimeError):
    """An error arising from B source which is well-formed in terms of grammar
    but is meaningless in terms of semantics.

    """

class InternalCompilerError(RuntimeError):
    """An error raised when an invalid AST has been created in a manner which
    should not be possible to trigger from B source.

    """

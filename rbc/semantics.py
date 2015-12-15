"""
Convert parsed grammar into AST nodes.

"""
from future.builtins import bytes

# Semantics
# =========
#
# A semantics object is used by the parser to construct AST nodes. Our semantics
# converts parser AST nodes which reflect the mechanism of the parser into AST
# nodes which better reflect the semantics of the program. For example, in the
# parser binary operator expressions are parsed as a higher precedence
# expression followed by zero or more operator, expression pairs. The semantics
# object converts those into zero or more BinaryOpValue AST nodes.

class BSemantics(object):
    """The BSemantics class represents the transformation of a parsed B program
    into AST nodes.

    The semantics are provided with a callable which is used to generate new AST
    nodes. The callable should take a single positional argument which is a
    string specifying the AST node name and a set of zero or more keyword
    arguments giving the parameters to the node.

    Args:
        make_node (callable): callable used to make new AST nodes

    """
    def __init__(self, make_node):
        # A callable which takes an AST node name and set of keyword arguments
        # and returns the corresponding AST node object.
        self._node = make_node

    # Programs
    # ========
    #
    # The "program" rule returns the B Program itself.

    def program(self, definitions):
        return self._node('Program', definitions=definitions)

    # Global definitions
    # ==================
    #
    # Programs consist of zero or more top-level definitions. These definitions
    # may be functions or initialised external variables.

    def simpledef(self, ast):
        return self._node('SimpleDefinition', name=ast.name, init=ast.init)

    def vectordef(self, ast):
        ivals = ast.ivals if ast.ivals is not None else []
        return self._node('VectorDefinition', name=ast.name,
                          maxidx=ast.maxidx, ivals=ivals)

    def functiondef(self, ast):
        args = ast.args if ast.args is not None else []
        return self._node(
            'FunctionDefinition', name=ast.name, arg_names=args,
            body=ast.body)

    # Statements
    # ==========
    #
    # A function body is a single statement. However statements may include
    # other statements.

    def _coalesce_statements(self, statements):
        """Accept a sequence of zero or more statements and return an AST node
        which is one of a statement, null statement or multipart statement as
        appropriate.

        """
        if len(statements) == 0:
            return self._node('ExpressionStatement', expression=None)
        elif len(statements) == 1:
            return statements[0]
        else:
            return self._node('MultipartStatement', statements=statements)

    def autostatement(self, substatements):
        return self._coalesce_statements(substatements)

    def autovar(self, ast):
        if ast.maxidx is None:
            return self._node('AutoStatement', name=ast.name)
        return self._node('AutoVectorStatement', name=ast.name,
                          maxidx=ast.maxidx)

    def extrnstatement(self, names):
        statements = [self._node('ExtrnStatement', name=name) for name in names]
        return self._coalesce_statements(statements)

    def compoundstatement(self, statements):
        return self._node('CompoundStatement', statements=statements)

    def ifstatement(self, ast):
        return self._node('IfStatement', cond=ast.cond, then=ast.then,
                          otherwise=ast.otherwise)

    def whilestatement(self, ast):
        return self._node('WhileStatement', cond=ast.cond, body=ast.body)

    def returnstatement(self, ast):
        return self._node('ReturnStatement', return_value=ast.return_value)

    def exprstatement(self, expression):
        return self._node('ExpressionStatement', expression=expression)

    def nullstatement(self, _):
        return self._node('NullStatement')

    def labelstatement(self, ast):
        return self._node('LabelStatement', label=ast.label,
                          statement=ast.statement)

    def gotostatement(self, ast):
        return self._node('GotoStatement', label=ast.label)

    def switchstatement(self, ast):
        return self._node('SwitchStatement', rvalue=ast.rvalue, body=ast.body)

    def casestatement(self, ast):
        return self._node('CaseStatement', cond=ast.cond, then=ast.then)

    def breakstatement(self, _):
        return self._node('BreakStatement')

    # Expressions
    # ===========

    def assignexpr(self, ast):
        if ast.op is None:
            return ast.lhs
        return self._node('AssignmentOpValue', lhs=ast.lhs, op=ast.op,
                          rhs=ast.rhs)

    def condexpr(self, ast):
        if ast.then is None:
            return ast.cond
        return self._node('ConditionalOpValue', cond=ast.cond, then=ast.then,
                          otherwise=ast.otherwise)

    def _leftbinopexpr(self, ast):
        """All left-to-right binary operators are handled similarly."""
        lhs = ast.lhs
        for tail_elem in ast.tail:
            lhs = self._node('BinaryOpValue', lhs=lhs, op=tail_elem.op,
                             rhs=tail_elem.rhs)
        return lhs

    def orexpr(self, ast):
        return self._leftbinopexpr(ast)

    def xorexpr(self, ast):
        return self._leftbinopexpr(ast)

    def andexpr(self, ast):
        return self._leftbinopexpr(ast)

    def eqexpr(self, ast):
        return self._leftbinopexpr(ast)

    def relexpr(self, ast):
        return self._leftbinopexpr(ast)

    def shiftexpr(self, ast):
        return self._leftbinopexpr(ast)

    def addexpr(self, ast):
        return self._leftbinopexpr(ast)

    def multexpr(self, ast):
        return self._leftbinopexpr(ast)

    def unaryexpr(self, ast):
        val = ast.rhs

        # Binding of unary ops is right-to-left
        for op in reversed(ast.rightops):
            val = self._node('RightUnaryOpValue', op=op, lhs=val)

        for op in reversed(ast.leftops):
            val = self._node('LeftUnaryOpValue', op=op, rhs=val)

        return val

    def primaryexpr(self, ast):
        val = ast.head

        if ast.tail is None:
            return val

        # Primary expressions bind left-to-right
        for tail_elem in ast.tail:
            if tail_elem.index is not None:
                # A vector expression is syntactic sugar for addition and
                # dereference.
                addr = self._node('BinaryOpValue', op='+', lhs=val,
                                  rhs=tail_elem.index)
                val = self._node('DereferencedRValue', rvalue=addr)
            else:
                # Otherwise, this is a function call
                args = tail_elem.args if tail_elem.args is not None else []
                val = self._node('FunctionCallValue', func=val, args=args)

        return val

    def variableexpr(self, name):
        return self._node('ScopeValue', name=name)

    def builtinexpr(self, ast):
        return self._node('BuiltinValue', name=ast)

    def numericexpr(self, ast):
        string_value = ''.join(ast)

        # Leading 0 implies octal
        if string_value.startswith('0'):
            int_value = int(string_value, 8)
        else:
            int_value = int(string_value, 10)

        return self._node('ConstantIntValue', value=int_value)

    def characterexpr(self, characters):
        val = 0
        for ch in _expand_escapes(characters):
            val = 0x100 * val + ch
        return self._node('ConstantIntValue', value=val)

    def stringexpr(self, characters):
        str_val = bytes(list(_expand_escapes(characters)))
        return self._node('StringConstantValue', value=str_val)

    # Names
    # =====

    def name(self, ast):
        return ast.head + ''.join(ast.tail)

def _expand_escapes(characters):
    """Return a generator which yields byte-sized character
    values from the sequence *characters*, replacing escape
    sequences.

    """
    ESCAPE_SEQUENCES = {
        '*0': '\0', '*e': '\x04', '*(': '{', '*)': '}',
        '*t': '\t', '**': '*', "*'": "'", '*"': '"',
        '*n': '\n'
    }

    for ch in characters:
        if len(ch) == 1:
            yield ord(ch)
        else:
            try:
                yield ord(ESCAPE_SEQUENCES[ch])
            except KeyError:
                raise ValueError(
                    'Unknown escape sequence: {}'.format(ch))

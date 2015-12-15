_PROGRAM = '''
    main() {
        extrn putstr, msg;
        auto i;
        i = 0;
        while(i < 3) { putstr(msg[i++]); }
    }
    msg [] "Hello,", " world!", "*n";
'''

def _parse(make_node, source=None, start='program'):
    """Parse B source code using a specified AST node constructor. If source is
    omitted, use _PROGRAM."""
    from rbc.parser import BParser
    from rbc.semantics import BSemantics
    source = source if source is not None else _PROGRAM
    return BParser().parse(source, start, semantics=BSemantics(make_node))

def test_ordered_dict():
    from rbc.dumpast import make_ordered_dict_ast_node
    node = _parse(make_ordered_dict_ast_node)
    assert '_type' in node

def test_json():
    from rbc.dumpast import make_ordered_dict_ast_node, ASTJSONEncoder
    node = _parse(make_ordered_dict_ast_node)
    assert len(ASTJSONEncoder().encode(node)) > 0

def test_graphviz():
    try:
        from io import StringIO
    except ImportError:
        from StringIO import StringIO
    from rbc.dumpast import make_ordered_dict_ast_node, GraphvizAST
    ast = GraphvizAST()
    node = _parse(ast.make_node)
    fobj = StringIO()
    ast.emit(fobj)
    assert len(fobj.getvalue()) > 0


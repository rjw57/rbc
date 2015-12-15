"""
Usage:
    dumpast.py (--json | --dot) [-p TERM] [<file>]

Options:
    -p TERM     Start parsing from the given term. [default: program]
    --json      Output in JSON format.
    --dot       Output in Graphviz format.

If <file> is omitted, input is read from standard input.

"""
from __future__ import unicode_literals

import collections
import json
import sys

from future.builtins import bytes

import docopt

from rbc.parser import BParser
from rbc.semantics import BSemantics

# A debugging tool for dumping ASTs in JSON or Graphviz format.

def make_ordered_dict_ast_node(type_, **kwargs):
    """Return a collections.OrderedDict with the type as the first value
    with key "_type".
    """
    od = collections.OrderedDict(_type=type_)
    od.update(**kwargs)
    return od

class ASTJSONEncoder(json.JSONEncoder):
    """An extended JSON encoder which can handle the types in AST nodes."""
    # pylint: disable=method-hidden
    def default(self, obj):
        if isinstance(obj, bytes):
            return repr(obj)
        return json.JSONEncoder.default(self, obj)

def escape_label(label):
    label = label.replace('\\', '\\\\')
    label = label.replace('"', '\\"')
    label = label.replace('<', '\\<')
    label = label.replace('>', '\\>')
    label = label.replace('|', '\\|')
    label = label.replace('{', '\\{')
    label = label.replace('}', '\\}')
    return label

class GraphvizAST(object):
    Node = collections.namedtuple('Node', 'name fields')

    def __init__(self):
        # A list of Node instances
        self._nodes = []

        # A set of Node pairs
        self._edges = set()

    def make_node(self, type_, **kwargs):
        # Each node has a unique id
        name = 'Node{}'.format(len(self._nodes))
        fields = [type_]

        items = list(kwargs.items())

        # Sort the items so that the order is at least consistent
        items = sorted(items, key=lambda item: item[0])

        extended_items = []
        for k, v in items:
            if isinstance(v, list) and len(v) > 0:
                extended_items.extend(('{}[{}]'.format(k, vidx), velem)
                                      for vidx, velem in enumerate(v))
            else:
                extended_items.append((k, v))

        for k, v in extended_items:
            if isinstance(v, GraphvizAST.Node):
                self._edges.add((
                    '{}:<f{}>'.format(name, len(fields)),
                    '{}:<f0>'.format(v.name)
                ))
                fields.append(k)
            else:
                fields.append('{}: {}'.format(k, v))

        # Return the new node
        node = GraphvizAST.Node(name=name, fields=tuple(fields))
        self._nodes.append(node)
        return node

    def emit(self, fobj):
        fobj.write('digraph {\n')
        fobj.write('graph [ rankdir="LR" ]; node [ shape=record ];\n')

        for node in self._nodes:
            label = ' | '.join('<f{}> {}'.format(idx, escape_label(label))
                               for idx, label in enumerate(node.fields))
            fobj.write('{} [ label="{}" ] ;\n'.format(node.name, label))

        for a, b in self._edges:
            fobj.write('{} -> {} ;\n'.format(a, b))

        fobj.write('\n}\n')

def main():
    opts = docopt.docopt(__doc__)
    if opts['<file>'] is not None:
        with open(opts['<file>']) as fobj:
            source = fobj.read()
    else:
        source = sys.stdin.read()

    if opts['--dot']:
        ast = GraphvizAST()
        out_format = 'dot'
        make_node = ast.make_node
    elif opts['--json']:
        out_format = 'json'
        make_node = make_ordered_dict_ast_node
    else:
        raise RuntimeError('No output format in options')

    node = BParser().parse(source, opts['-p'], semantics=BSemantics(make_node))

    if out_format == 'json':
        encoder = ASTJSONEncoder(indent=2)
        for chunk in encoder.iterencode(node):
            sys.stdout.write(chunk)
        sys.stdout.write('\n')
    else:
        ast.emit(sys.stdout)

if __name__ == '__main__':
    main()

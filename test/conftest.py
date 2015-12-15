import pytest

@pytest.fixture(scope='session')
def compile_b():
    """A function which compiles B source to a llvm ModuleRef."""
    from rbc import compiler
    options = compiler.CompilerOptions()
    def _compile_b(source):
        mod_asm = compiler.compile_b_source(source, options)
        mod = compiler.optimize_module(mod_asm, options)
        return mod
    return _compile_b

@pytest.fixture()
def output_from(tmpdir):
    """A function which takes a string with B source, compiles and executes it
    returning the output as a string."""
    import subprocess
    import rbc.compiler
    b_source = tmpdir.join('test.b').strpath
    executable = tmpdir.join('test').strpath
    def _output_from(source):
        with open(b_source, 'w') as fobj:
            fobj.write(source)
        rbc.compiler.compile_and_link(executable, [b_source])
        return subprocess.check_output([executable])
    return _output_from

@pytest.fixture
def check_output(output_from):
    """A function which takes a string with B source, compiles and executes it
    and then compares the output with an expected value."""
    import codecs
    def _check_output(source, expected):
        output = output_from(source)
        assert output == codecs.encode(str(expected), 'utf8')
    return _check_output

@pytest.fixture
def check_expr(check_output):
    """A function which takes an expression as a string, construct a B program
    which evaluates the expression and prints it using putnumb and compares it
    to an expected output."""
    def _check_expr(expr, expected):
        check_output('''
            main() {
                extrn putnumb;
                auto v;
                v = (''' + str(expr) + ''');
                putnumb(v);
            }
        ''', str(expected))
    return _check_expr

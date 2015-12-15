def test_empty_module(compile_b):
    compile_b('')

def test_empty_function_is_defined(compile_b):
    compile_b('f(){}')

def test_return_argument(compile_b):
    compile_b('f(arg){ return (arg); }')

def test_return_constant(compile_b):
    compile_b('f(){ return (42); }')

def test_return_nothing(compile_b):
    compile_b('f(){ return; }')

def test_return_function(compile_b):
    compile_b('f1(){} f2(){ return (f1); }')

def test_return_not_yet_defined_function(compile_b):
    compile_b('f1(){ return(f2); } f2(){}')

def test_return_simple_extern(compile_b):
    compile_b('f(){ extrn A; return(A); } A;')

def test_return_deref_extern(compile_b):
    compile_b('f1(){} f2(){return(&f1);}')

def test_extern_function_call(compile_b):
    compile_b('f1(){ extrn putchar; putchar(65); }')

def test_names_with_backspace(compile_b):
    compile_b('m\byfunc(){ }')

def test_simple_expression(check_output):
    check_output('main() { extrn putnumb; putnumb(2-3-4); }', '-5')
    check_output('main() { extrn putnumb; putnumb(4+10*2); }', '24')
    check_output('main() { extrn putnumb; putnumb(5 & 2); }', '0')
    check_output('main() { extrn putnumb; putnumb(7 & 2); }', '2')

def test_func_call(check_output):
    check_output('''
        main() { extrn putnumb; putnumb(sub(3,4)); }
        sub(a, b) { return (a-b); }
    ''', '-1')

def test_simple_auto(check_output):
    check_output('''
        main() {
            extrn putnumb;
            auto a, b;
            a = 4; b = 10;
            putnumb(b-a);
        }
    ''', '6')

def test_hello_world(check_output):
    check_output('''
        main() {
            extrn putchar;
            putchar('hell');
            putchar('o, w');
            putchar('orld');
        }
    ''', 'hello, world')

def test_recursion(check_output):
    check_output('''
        fact(n) if(n == 0) return(1); else return (n*fact(n-1));
        check(a, b) {
            extrn putchar;
            if(a != b)
                putchar('x');
            else
                putchar('.');
        }
        main() {
            check(fact(0), 1);
            check(fact(1), 1);
            check(fact(2), 2);
            check(fact(3), 6);
            check(fact(4), 24);
        }
    ''', '.....')

def test_zero_extrn(check_output):
    check_output('''
        main() {
            extrn a, putnumb;
            putnumb(a + 5);
        }
        a;
    ''', '5')

def test_extrn_hello_world(check_output):
    check_output('''
        main() {
            extrn a, b, c, putchar;
            putchar(a); putchar(b); putchar(c); putchar('!*n');
        }
        a 'hell';
        b 'o, w';
        c 'orld';
    ''', 'hello, world!\n')

def test_extrn_hello_world_2(check_output):
    check_output('''
        main( ) {
            extrn a,b,c,d;
            put2char(a,b) ;
            put2char(c,d) ;
        }
        put2char(x,y) {
            extrn putchar;
            putchar(x);
            putchar(y);
        }
        a 'hell'; b 'o, w'; c 'orld'; d '!*n';
    ''', 'hello, world!\n')

def test_setting_extrn(check_output):
    check_output('''
        main() {
            extrn putnumb, val;
            addval(5);
            addval(3);
            putnumb(val);
        }
        addval(x) {
            extrn val;
            val =+ x;
        }
        val;
    ''', '8')


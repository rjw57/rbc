def test_constant_decimal(check_expr):
    check_expr('25', 25)

def test_constant_octal(check_expr):
    # Real programmers think Halloween is on the same day as Christmas
    check_expr('031', 25)

def test_add_mult_precedence(check_expr):
    # Subtraction binds LTR
    check_expr('2-3-4', -5)
    # Division binds LTR
    check_expr('20/5/2', 2)
    # Addition higher precedence than multiplication
    check_expr('2*4+5*3', 23)
    # Brackets override precedence
    check_expr('2*(4+5)*3', 54)

def test_basic_relational(check_expr):
    check_expr('6>5', '1')
    check_expr('5>5', '0')
    check_expr('4>5', '0')
    check_expr('4>=5', '0')
    check_expr('5>=5', '1')
    check_expr('6>=5', '1')
    check_expr('6<5', '0')
    check_expr('5<5', '0')
    check_expr('4<5', '1')
    check_expr('4<=5', '1')
    check_expr('5<=5', '1')
    check_expr('6<=5', '0')
    check_expr('6==5', '0')
    check_expr('5==5', '1')
    check_expr('6!=5', '1')
    check_expr('5!=5', '0')

def test_char_constant(check_expr):
    check_expr("''", '0')
    check_expr("'A'", '65')
    check_expr("'ab'", '24930')
    check_expr("'a*0'", '24832')
    check_expr("'*''", '39')
    check_expr("' x '", '2127904')

def test_unary_binding(check_expr):
    check_expr('-~0', '1')

def test_assignment_op(check_output):
    def check(op, expected):
        check_output('main(){extrn putnumb;auto a;a=10;a'+op+' 2;putnumb(a);}',
                     expected)
    check('=', '2')
    check('=-', '8')
    check('=+', '12')
    check('=*', '20')
    check('=/', '5')
    check('=%', '0')

def test_assignment_op_has_value(check_output):
    check_output('''
        main() {
            extrn a, putnumb;
            auto b, c;
            putnumb(c=b=(a==23));
            putnumb(c);
            putnumb(b);
            putnumb(a);
        }
        a 23;
    ''', '11123')

def test_builtin_bytes_per_word(output_from):
    bpw = output_from('''
        main() {
            extrn putnumb;
            putnumb(__bytes_per_word);
        }
    ''')
    assert bpw != ''
    bpw_val = int(bpw)
    assert bpw_val > 0

def test_inline_string_constants(check_output):
    check_output('''
        main() {
            extrn putstr;
            putstr("hello, "); putstr("world!"); putstr("*n");
        }
    ''', 'hello, world!\n')

def test_auto_string_constants(check_output):
    check_output('''
        main() {
            extrn putstr;
            auto s1, s2;
            s1 = "hello, "; s2 = "world!*n";
            putstr(s1); putstr(s2);
        }
    ''', 'hello, world!\n')

def test_extern_string_constants(check_output):
    check_output('''
        main() {
            extrn putstr, s1, s2;
            putstr(s1); putstr(s2);
        }
        s1 "hello, "; s2 "world!*n";
    ''', 'hello, world!\n')

def test_conditional_op(check_expr):
    check_expr('5>6?2:3', '3')
    check_expr('5<6?2:3', '2')
    check_expr('0?2:3?4:5', '4')

def test_conditional_evaluates_one_side(check_output):
    check_output('''
        main() {
            1<2 ? f(10):f(11);
            5>9 ? f(20):f(21);
        }
        f(x) {
            extrn putnumb;
            putnumb(x);
            return (x);
        }
    ''', '1021')


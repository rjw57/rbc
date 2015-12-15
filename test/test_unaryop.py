def test_not_operator(check_expr):
    check_expr('!5', '0')
    check_expr('!-1', '0')
    check_expr('!1', '0')
    check_expr('!0', '1')

def test_minus(check_expr):
    check_expr('-5', '-5')
    check_expr('-0', '0')

def test_reference(check_output):
    check_output('''
        main() {
            extrn v, putnumb;
            putnumb(*(v+1));
        }
        v[] 1, 2, 3;
    ''', 2)

def test_dereference(check_output):
    check_output('''
        main() {
            extrn putnumb;
            auto i;
            i = 56;
            putataddr(&i);
            putnumb(i);
        }
        putataddr(addr) { extrn putnumb; putnumb(*addr); *addr=0; }
    ''', '560')

def test_preinc(check_output):
    check_output('''
        main() { extrn putnumb; auto i; i=4; putnumb(++i); putnumb(i); }
    ''', '55')

def test_predec(check_output):
    check_output('''
        main() { extrn putnumb; auto i; i=4; putnumb(--i); putnumb(i); }
    ''', '33')

def test_postinc(check_output):
    check_output('''
        main() { extrn putnumb; auto i; i=4; putnumb(i++); putnumb(i); }
    ''', '45')

def test_postdec(check_output):
    check_output('''
        main() { extrn putnumb; auto i; i=4; putnumb(i--); putnumb(i); }
    ''', '43')

def test_dereference_via_flip(check_output):
    check_output('''
        flip(x, y) { auto t; t = *y; *y = *x; *x = t; }
        main() {
            extrn putnumb;
            auto a, b;
            a = 10; b = 20;
            putnumb(a); putnumb(b);
            flip(&a, &b);
            putnumb(a); putnumb(b);
        }
    ''', '10202010')

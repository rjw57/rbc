def test_basic_switch(check_output):
    check_output('''
        main() {
            extrn putchar;;
            auto i;
            i = 0; while(i <= 4) {
                describe(i);
                putchar('*n');
                ++i;
            }
        }
        describe(val) {
            extrn putstr, putnumb;
            putnumb(val); putstr(" is ");
            switch(val) {
                case 0: putstr("zero"); break;
                case 1: putstr("one"); break;
                default: putstr("many"); break;
            }
        }
    ''', '0 is zero\n1 is one\n2 is many\n3 is many\n4 is many\n')

def test_fallthrough(check_output):
    check_output('''
        main() {
            extrn putchar;;
            auto i;
            i = 0; while(i <= 4) {
                describe(i);
                putchar('*n');
                ++i;
            }
        }
        describe(val) {
            extrn putstr, putnumb;
            putnumb(val); putstr(" is ");
            switch(val) {
                case 0: putstr("zero");
                case 1: putstr("one"); break;
                default: putstr("many");
            }
        }
    ''', '0 is zeroone\n1 is one\n2 is many\n3 is many\n4 is many\n')


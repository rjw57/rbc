def test_count_down(check_output):
    check_output('''
        countdown(num) {
            extrn putnumb;
            while(num > 0) { putnumb(num); num =- 1; }
        }
        main() {
            countdown(5);
        }
    ''', '54321')

def test_null_statement(check_output):
    check_output('main(){while(0);}', '')

def test_break(check_output):
    check_output('''
        main() {
            auto i;
            extrn putchar;
            i = 0; while(i < 100) {
                putchar('.');
                if(++i >= 4)
                    break;
            }
        }
    ''', '....')

def test_break_is_no_op_outside_while(check_output):
    check_output('''
        main() { extrn putchar; break; putchar('X'); }
    ''', 'X')





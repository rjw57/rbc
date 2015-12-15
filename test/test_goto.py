def test_simple_goto(check_output):
    check_output('''
        main() {
            auto i;
            extrn putchar;
            putchar('X');
            i = 0;
        loop:
            putchar('.');
            if(++i != 5) goto loop;
            putchar('Y');
        }
    ''', 'X.....Y')

def test_goto_future(check_output):
    check_output('''
        main() {
            auto i;
            extrn putchar;
            putchar('X');
            i = 0;
        loop:
            putchar('.');
            if(++i == 5) goto exit;
            goto loop;
        exit:
            putchar('Z');
        }
    ''', 'X.....Z')

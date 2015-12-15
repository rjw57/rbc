def test_simple_comment(check_output):
    check_output('''
        main() {
            extrn putchar;
            /* a comment */
            putchar('a');
        }
    ''', 'a')

def test_comment_stops_at_first_terminator(check_output):
    check_output('''
        main() {
            extrn putchar;
            /* a comment */
            putchar('a');
            /* another comment */
        }
    ''', 'a')


def test_comment_accepts_initial_asterisk(check_output):
    check_output('''
        main() {
            extrn putchar;
            /** a comment */
            putchar('a');
        }
    ''', 'a')


def test_comment_accepts_final_asterisk(check_output):
    check_output('''
        main() {
            extrn putchar;
            /* a comment **/
            putchar('a');
        }
    ''', 'a')


def test_comment_accepts_medial_asterisk(check_output):
    check_output('''
        main() {
            extrn putchar;
            /* a * comment */
            putchar('a');
        }
    ''', 'a')

def test_comment_accepts_newline(check_output):
    check_output('''
        main() {
            extrn putchar;
            /* a
            multi
            line
            comment */
            putchar('a');
        }
    ''', 'a')


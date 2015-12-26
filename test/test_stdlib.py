def test_char(check_output):
    check_output('''
        main() {
            extrn char, putchar, s;
            auto i;
            i = 0; while(i <=4) {
                putchar('>'); putchar(char(s, i)); putchar('<');
                ++i;
            }
        }
        s "hello";
    ''', '>h<>e<>l<>l<>o<')

def test_lchar(check_output):
    check_output('''
        main() {
            extrn lchar, putstr;
            auto s[3];
            lchar(s, 0, 'X');
            lchar(s, 1, 'Y');
            lchar(s, 2, 'Z');
            lchar(s, 3, '*e');
            putstr(s);
        }
    ''', 'XYZ')

def test_printn(check_output):
    check_output('''
        main() {
            extrn printn, putchar;
            printn(42, 2); putchar('*n');
            printn(42, 8); putchar('*n');
            printn(42, 10); putchar('*n');
        }
    ''', '101010\n52\n42\n')

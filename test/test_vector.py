def test_auto_vector(check_output):
    check_output('''
        main() {
            extrn putchar;
            auto v[2], i;
            v[0] = 'a';
            v[1] = 's';
            v[2] = 't';
            i = 0;
            while(i <= 2) {
                putchar(v[i]); i =+ 1;
            }
        }
    ''', 'ast')

def test_auto_with_strings(check_output):
    check_output('''
        main() {
            extrn greeting, putstr;
            auto v[2], i;
            v[0] = greeting;
            v[1] = ", ";
            v[2] = "world!*n";
            i = 0;
            while(i <= 2) {
                putstr(v[i]); i =+ 1;
            }
        }
        greeting "hello";
    ''', 'hello, world!\n')

def test_uninit_external_vector(check_output):
    # Technically the initial contents of v are undefined but our implementation
    # always fills external vectors with zeros.
    check_output('''
        main() {
            extrn v, putnumb;
            auto i;
            i = 0;
            v[2] = 8;
            while(i <= 4) { putnumb(v[i]); i =+ 1; }
        }
        v[4];
    ''', '00800')

def test_init_external_vector(check_output):
    check_output('''
        main() {
            extrn v, putnumb;
            auto i;
            i = 0;
            v[2] = 8;
            while(i <= 4) { putnumb(v[i]); i =+ 1; }
        }
        v[4] 12, 34;
    ''', '1234800')

def test_init_external_str_vector(check_output):
    check_output('''
        main() {
            extrn v, putstr;
            auto i;
            i = 0;
            while(i <= 2) { putstr(v[i]); i =+ 1; }
        }
        v[2] "one", "two", "three";
    ''', 'onetwothree')

def test_init_vector_no_count(check_output):
    check_output('''
        main() {
            extrn v, putnumb;
            auto i;
            i = 0;
            while(i <= 2) { putnumb(v[i]); i =+ 1; }
        }
        v[] 1, 2, 3;
    ''', '123')

def test_init_vector_too_few_count(check_output):
    check_output('''
        main() {
            extrn v, putnumb;
            auto i;
            i = 0;
            while(i <= 2) { putnumb(v[i]); i =+ 1; }
        }
        v[1] 1, 2, 3;
    ''', '123')

def test_init_vector_too_many_count(check_output):
    check_output('''
        main() {
            extrn v, putnumb;
            auto i;
            i = 0;
            while(i <= 6) { putnumb(v[i]); i =+ 1; }
        }
        v[6] 1, 2, 3;
    ''', '1230000')

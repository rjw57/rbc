def test_simple_if(check_output):
    check_output('''
        main(){
            extrn putnumb;
            if(0) putnumb(1);
            if(1) putnumb(2);
            if(-1) putnumb(3);
            if(42) putnumb(4);
            if(-42) putnumb(5);
        }
    ''', '2345')

def test_if_based_return(check_output):
    check_output('''
        max(a, b) {
            if(a > b) return(a);
            return(b);
        }
        main() {
            extrn putnumb;
            putnumb(max(9, -7));
            putnumb(max(3, 5));
        }
    ''', '95')

def test_simple_if_else(check_output):
    check_output('''
        putargmax(a,b) {
            extrn putnumb;
            if(a>=b) putnumb(0); else putnumb(1);
        }
        main() {
            putargmax(10, 10);
            putargmax(10, 11);
            putargmax(5, 4);
        }
    ''', '010')

def test_else_binds_to_inner_if(check_output):
    check_output('''
        posnegzero(a) {
            if(a != 0) if(a > 0) return (1); else return(-1);
            return(0);
        }
        main() {
            extrn putnumb;
            putnumb(posnegzero(-2));
            putnumb(posnegzero(-1));
            putnumb(posnegzero( 0));
            putnumb(posnegzero( 1));
            putnumb(posnegzero( 2));
        }
    ''', '-1-1011')


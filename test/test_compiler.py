import rbc.compiler as compiler

def test_putchar(check_output):
    check_output('main() { extrn putchar; putchar(65); }', 'A')

def test_putnumb(check_output):
    check_output('main() { extrn putnumb; putnumb(-010); }', '-8')


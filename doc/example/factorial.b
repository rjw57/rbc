/* The traditional example of a recursive function: the factorial */

fact(n) return (n==0?1:n*fact(n-1));

main() {
    extrn putnumb, putchar;
    auto x;
    x = 0;
    while(x <= 20) {
        putnumb(x); putchar('! = '); putnumb(fact(x)); putchar('*n');
        x++;
    }
}


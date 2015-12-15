/* From section 15 of tutorial: "This terse example reads one line from the
 * terminal, and prints each non-blank string of characters on a separate line:
 * one or more blanks are converted into a single newline." */
main( ) {
    auto c;
    while (1) {
        while ( (c=getchar()) != ' ')
        if (putchar(c) == '*n') exit();
        putchar( '*n' );
        while ( (c=getchar()) == ' '); /* skip blanks */
        if (putchar(c)=='*n') exit(); /* done when newline */
    }
}

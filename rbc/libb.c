#include <inttypes.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

/* B word type is integer type which can hold a pointer. */
typedef intptr_t word_t;

/* Number of bytes in a word */
#define BYTES_PER_WORD (sizeof(word_t))

/* GCC, clang and work-alike compilers provide the predefined macro
 * __USER_LABEL_PREFIX__. This expands to a single token which is the prefix
 * used on symbol names visible to C. This is also the prefix added to symbols
 * emitted by LLVM. On Linux-y machines this tends to be empty but on OS X (and,
 * I think, Windows) this is an underscore.
 *
 * (See https://gcc.gnu.org/onlinedocs/cpp/Stringification.html for the source
 * of the mysterious STRINGIFY and X_STRINGIFY macros. */
#define X_STRINGIFY(s) STRINGIFY(s)
#define STRINGIFY(s) #s
#define B_SYMBOL_PREFIX_STR X_STRINGIFY(__USER_LABEL_PREFIX__) "b."

/* Define functions using this macro which sets symbol names for functions since
 * B symbol names are not valid C identifiers. Additionally, B needs *all*
 * pointers to be aligned to word boundaries, including function pointers. */
#define B_FUNCTION(name, args) \
    extern word_t b_ ## name args asm(B_SYMBOL_PREFIX_STR #name) ; \
    word_t __attribute__((aligned(BYTES_PER_WORD))) b_ ## name args

/* Main entry point */
B_FUNCTION(main, ());

int main() {
    b_main();
    return EXIT_SUCCESS;
}

/* Put a characters in word to standard out. */
B_FUNCTION(putchar, (word_t c)) {
    for(int i=BYTES_PER_WORD-1; i>=0; i--) {
        /* Get i-th byte */
        int ibyte = (c>>(i*8)) & 0xff;
        if(ibyte != '\0') {
            /* To this day, putchar exists in the C standard library and takes
             * an integer argument. */
            putchar(ibyte);
        }
    }
    return c;
}

/* Put word as a signed integer to standard out. */
B_FUNCTION(putnumb, (word_t n)) {
    printf("%" PRIdPTR, n);
    return n;
}

/* Read character from standard input. */
B_FUNCTION(getchar, ()) {
    /* C imitates B. */
    return getchar();
}

/* Exit process. */
B_FUNCTION(exit, ()) {
    /* C imitates B. */
    exit(EXIT_SUCCESS);
    return 0;
}

/* Put string up to terminating *e. */
B_FUNCTION(putstr, (word_t s_ptr)) {
    /* Addresses in B are word-oriented. */
    char *s = (char*)(s_ptr * BYTES_PER_WORD);
    while(*s != '\04') {
        putchar(*s); ++s;
    }
    return 0;
}

/* returns the value of the nth ascii character, in the string s, right
 * justified with zero fill. Characters are numbered from left to right,
 * starting at zero. Thus char("abc",1) returns 'b'. */
B_FUNCTION(char, (word_t s_ptr, word_t n)) {
    /* Addresses in B are word-oriented. */
    char *s = (char*)(s_ptr * BYTES_PER_WORD);
    return s[n];
}

/* This function replaces the nth ascii character of string s by the rightmost
 * eight bits of word c. c is returned as a value. Thus, if s has the value
 * "abc", lchar(s,1,'x') returns the value 'x', and sets s to have the value
 * "axc". */
B_FUNCTION(lchar, (word_t s_ptr, word_t n, word_t c)) {
    /* Addresses in B are word-oriented. */
    char *s = (char*)(s_ptr * BYTES_PER_WORD);
    s[n] = c;
}

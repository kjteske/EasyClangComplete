#include <iostream>


#define STDOUT(x) std::cout << x

#define MACRO_WITH_ARGS(x,y,z)
 # define   MACRO_WITH_EXTRA_SPACES(     x, y     ,    z    )

/// Doxy comment
#define MY_MACRO_FUNC(x) STDOUT(x)

#define MY_MACRO_FUNC_NO_ARGS() 

#define VARIADIC_MACRO(...) 

#define MACRO_EMPTY
#define MACRO_VALUE 1

namespace 
{
    const int anon = 1;
}

static int bar()
{
    return 1;
}

int foo()
{
    int x = 0;
    MY_MACRO_FUNC(x + 2 / bar() + anon);
    MY_MACRO_FUNC_NO_ARGS()
    MACRO_EMPTY
    MACRO_WITH_ARGS(1, 2, 3)
    MACRO_WITH_EXTRA_SPACES(1, 2, 3)
    VARIADIC_MACRO()
    VARIADIC_MACRO(1)
    VARIADIC_MACRO(3, 4)
    x = MACRO_VALUE;
    STDOUT("words");
    return x;
}


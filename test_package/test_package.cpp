#include <iostream>
#include <sentry.h>

int main()
{
    std::cout << "run sentry-native tests\n";
    for (size_t i = 0; i < 10; i++)
    {
        sentry_options_t *options = sentry_options_new();
        sentry_options_set_environment(options, "release");
        sentry_init(options);
        sentry_shutdown();
    }
    std::cout << "reach end :-D\n";
    return 0;
}

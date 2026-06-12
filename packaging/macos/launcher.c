#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdio.h>
#include <mach-o/dyld.h>

static void strip_last(char *path) {
    char *p = strrchr(path, '/');
    if (p && p != path) *p = '\0';
}

int main(void) {
    char buf[4096];
    uint32_t sz = sizeof(buf);
    if (_NSGetExecutablePath(buf, &sz) != 0) return 1;

    char resolved[4096];
    if (!realpath(buf, resolved)) return 1;

    /* Walk up: filename → Contents/MacOS → Contents → .app → parent dir */
    strip_last(resolved);
    strip_last(resolved);
    strip_last(resolved);
    strip_last(resolved);

    char binary[4096];
    snprintf(binary, sizeof(binary), "%s/PyGoose", resolved);

    char cmd[8192];
    snprintf(cmd, sizeof(cmd), "xattr -cr \"%s\" 2>/dev/null", binary);
    system(cmd);

    char *argv[] = { binary, NULL };
    execv(binary, argv);
    return 1;
}

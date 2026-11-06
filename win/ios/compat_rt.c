// Stand-in for the part of Darwin's compiler-rt (libclang_rt.ios.a) that Objective-C / C code uses through @available / __builtin_available:
// LLVM's Windows release ships no Darwin runtime libraries, so win/build_app.py links this file when the clang resource folder has none.
// Same semantics as compiler-rt's os_version_check.c on current systems: ask dyld through _availability_version_check (libSystem, iOS 15 and later),
// which every iOS this app can run on (26 and later) provides.
#include <stdint.h>

typedef uint32_t dyld_platform_t;
typedef struct { dyld_platform_t platform; uint32_t version; } dyld_build_version_t;
extern _Bool _availability_version_check(uint32_t count, dyld_build_version_t versions[]);

static uint32_t pack(uint32_t major, uint32_t minor, uint32_t sub) { return (major << 16) | ((minor & 0xff) << 8) | (sub & 0xff); }

int32_t __isPlatformVersionAtLeast(uint32_t platform, uint32_t major, uint32_t minor, uint32_t sub) {
    dyld_build_version_t v = {platform, pack(major, minor, sub)};
    return _availability_version_check(1, &v);
}

int32_t __isOSVersionAtLeast(int32_t major, int32_t minor, int32_t sub) {   // the older entry point, for the platform the binary was built for (2 = iOS)
    return __isPlatformVersionAtLeast(2, (uint32_t)major, (uint32_t)minor, (uint32_t)sub);
}

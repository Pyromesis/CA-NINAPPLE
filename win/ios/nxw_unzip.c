// ZIP extraction for the app's "Import ZIP" (win/ios/DataHelp.m): a split build's data folder zipped on the PC (7-Zip, stored or Deflate, ZIP64 for the 17 GB of Tears of
// the Kingdom) is extracted by the app into its own Documents, straight from where the Files app keeps the archive (no copy of the archive first).
// Reads the central directory (ZIP64 end records when present), then each entry's local header and data; Deflate through zlib, stored entries copied.
// Names with "..", absolute paths or backslashes are refused. Everything goes into <dest>/.nxw_import first; the caller moves the top-level items into place
// when it returns 0, so a cancelled or failed import leaves nothing half-written in Documents.
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>

typedef void (*nxw_unzip_progress)(void *ctx, uint64_t done, uint64_t total, uint64_t files, uint64_t nfiles);

static int rd(int fd, void *b, size_t n, uint64_t off) {
    uint8_t *p = b;
    while (n) { ssize_t r = pread(fd, p, n, (off_t)off); if (r <= 0) return -1; p += r; n -= (size_t)r; off += (uint64_t)r; }
    return 0;
}
static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t u32(const uint8_t *p) { return (uint32_t)u16(p) | (uint32_t)u16(p + 2) << 16; }
static uint64_t u64(const uint8_t *p) { return (uint64_t)u32(p) | (uint64_t)u32(p + 4) << 32; }

static int mkdirs(char *path) {   // every parent folder of path (modifies and restores path)
    for (char *s = path + 1; *s; s++)
        if (*s == '/') { *s = 0; if (mkdir(path, 0755) && errno != EEXIST) { *s = '/'; return -1; } *s = '/'; }
    return 0;
}

static int write_all(int fd, const uint8_t *b, size_t n) {
    while (n) { ssize_t w = write(fd, b, n); if (w <= 0) return -1; b += w; n -= (size_t)w; }
    return 0;
}

// Returns 0, or -1 with a message in err. *cancel set by another thread stops it. Fills *total_out with the uncompressed size (for the free-space check, call with dry = 1)
int nxw_unzip(const char *zip, const char *stage, int dry, volatile int *cancel, nxw_unzip_progress cb, void *ctx, uint64_t *total_out, char *err, size_t errn) {
    int fd = open(zip, O_RDONLY); if (fd < 0) { snprintf(err, errn, "cannot open the ZIP (%s)", strerror(errno)); return -1; }
    int ret = -1; uint8_t *cd = NULL, *buf = NULL, *obuf = NULL; char *path = NULL;
    struct stat st; fstat(fd, &st); uint64_t size = (uint64_t)st.st_size;
    // End of central directory: in the last 64 KB + 22 bytes
    uint64_t scan = size < 65557 ? size : 65557; uint8_t *tail = malloc(scan);
    if (!tail || rd(fd, tail, scan, size - scan)) { snprintf(err, errn, "cannot read the ZIP's end"); free(tail); goto out; }
    int64_t e = -1; for (int64_t i = (int64_t)scan - 22; i >= 0; i--) if (u32(tail + i) == 0x06054b50) { e = i; break; }
    if (e < 0) { snprintf(err, errn, "not a ZIP file (no end of central directory)"); free(tail); goto out; }
    uint64_t nent = u16(tail + e + 10), cdsize = u32(tail + e + 12), cdoff = u32(tail + e + 16);
    if (e >= 20 && u32(tail + e - 20) == 0x07064b50) {   // ZIP64 end of central directory locator → record
        uint64_t z64 = u64(tail + e - 20 + 8); uint8_t r[56];
        if (rd(fd, r, 56, z64) || u32(r) != 0x06064b50) { snprintf(err, errn, "bad ZIP64 end record"); free(tail); goto out; }
        nent = u64(r + 32); cdsize = u64(r + 40); cdoff = u64(r + 48);
    }
    free(tail);
    if (cdoff + cdsize > size || cdsize > (1ull << 30)) { snprintf(err, errn, "bad central directory"); goto out; }
    cd = malloc(cdsize ? cdsize : 1); if (!cd || rd(fd, cd, cdsize, cdoff)) { snprintf(err, errn, "cannot read the central directory"); goto out; }
    // First pass: totals
    uint64_t total = 0, p = 0;
    for (uint64_t i = 0; i < nent; i++) {
        if (p + 46 > cdsize || u32(cd + p) != 0x02014b50) { snprintf(err, errn, "bad central directory entry %llu", (unsigned long long)i); goto out; }
        uint64_t us = u32(cd + p + 24); uint16_t nl = u16(cd + p + 28), xl = u16(cd + p + 30), cl = u16(cd + p + 32);
        if (us == 0xffffffff) for (uint64_t x = p + 46 + nl; x + 4 <= p + 46 + nl + xl; x += 4 + u16(cd + x + 2)) if (u16(cd + x) == 1) { us = u64(cd + x + 4); break; }
        total += us; p += 46 + nl + xl + cl;
    }
    if (total_out) *total_out = total;
    if (dry) { ret = 0; goto out; }
    size_t sl = strlen(stage); path = malloc(sl + 70000); buf = malloc(1 << 20); obuf = malloc(1 << 20);
    if (!path || !buf || !obuf) { snprintf(err, errn, "out of memory"); goto out; }
    uint64_t done = 0; p = 0;
    for (uint64_t i = 0; i < nent; i++) {
        if (cancel && *cancel) { snprintf(err, errn, "cancelled"); goto out; }
        uint16_t method = u16(cd + p + 10), nl = u16(cd + p + 28), xl = u16(cd + p + 30), cl = u16(cd + p + 32);
        uint64_t cs = u32(cd + p + 20), us = u32(cd + p + 24), lo = u32(cd + p + 42);
        for (uint64_t x = p + 46 + nl; x + 4 <= p + 46 + nl + xl; x += 4 + u16(cd + x + 2)) {
            if (u16(cd + x) != 1) continue;
            const uint8_t *z = cd + x + 4;   // ZIP64 extra: only the fields whose 32-bit value is 0xffffffff, in this order
            if (us == 0xffffffff) { us = u64(z); z += 8; }
            if (cs == 0xffffffff) { cs = u64(z); z += 8; }
            if (lo == 0xffffffff) { lo = u64(z); }
            break;
        }
        const char *name = (const char *)cd + p + 46;
        p += 46 + nl + xl + cl;
        if (!nl || name[0] == '/' || memchr(name, '\\', nl) || nl > 65000) { snprintf(err, errn, "unsafe name in the ZIP"); goto out; }
        for (uint16_t k = 0; k + 1 < nl; k++) if (name[k] == '.' && name[k + 1] == '.' && (k == 0 || name[k - 1] == '/') && (k + 2 == nl || name[k + 2] == '/')) { snprintf(err, errn, "unsafe name in the ZIP"); goto out; }
        memcpy(path, stage, sl); path[sl] = '/'; memcpy(path + sl + 1, name, nl); path[sl + 1 + nl] = 0;
        if (mkdirs(path)) { snprintf(err, errn, "cannot make folders (%s)", strerror(errno)); goto out; }
        if (name[nl - 1] == '/') continue;   // a folder entry
        uint8_t lh[30];
        if (rd(fd, lh, 30, lo) || u32(lh) != 0x04034b50) { snprintf(err, errn, "bad local header"); goto out; }
        uint64_t data = lo + 30 + u16(lh + 26) + u16(lh + 28);
        int of = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (of < 0) { snprintf(err, errn, "cannot write %s (%s)", name, strerror(errno)); goto out; }
        int bad = 0;
        if (method == 0) {
            for (uint64_t o = 0; o < cs && !bad; ) {
                size_t n = cs - o > (1 << 20) ? (1 << 20) : (size_t)(cs - o);
                if (rd(fd, buf, n, data + o) || write_all(of, buf, n)) bad = 1;
                o += n; done += n;
                if (cb && !((o >> 20) & 63)) cb(ctx, done, total, i, nent);
                if (cancel && *cancel) bad = 2;
            }
        } else if (method == 8) {
            z_stream zs; memset(&zs, 0, sizeof zs);
            if (inflateInit2(&zs, -MAX_WBITS) != Z_OK) bad = 1;
            uint64_t o = 0; int r = Z_OK;
            while (!bad && r != Z_STREAM_END) {
                if (!zs.avail_in) {
                    size_t n = cs - o > (1 << 20) ? (1 << 20) : (size_t)(cs - o);
                    if (!n || rd(fd, buf, n, data + o)) { bad = 1; break; }
                    o += n; zs.next_in = buf; zs.avail_in = (uInt)n;
                }
                zs.next_out = obuf; zs.avail_out = 1 << 20;
                r = inflate(&zs, Z_NO_FLUSH);
                if (r != Z_OK && r != Z_STREAM_END) { bad = 1; break; }
                size_t got = (1 << 20) - zs.avail_out;
                if (write_all(of, obuf, got)) bad = 1;
                done += got;
                if (cancel && *cancel) bad = 2;
            }
            inflateEnd(&zs);
        } else { snprintf(err, errn, "%s: compression method %u is not supported (zip it with 7-Zip as Store or Deflate)", name, method); close(of); goto out; }
        if (close(of)) bad = 1;
        if (bad == 2) { snprintf(err, errn, "cancelled"); goto out; }
        if (bad) { snprintf(err, errn, "cannot extract %s (%s)", name, errno ? strerror(errno) : "bad data"); goto out; }
        if (cb) cb(ctx, done, total, i + 1, nent);
    }
    ret = 0;
out:
    free(cd); free(buf); free(obuf); free(path); close(fd);
    return ret;
}

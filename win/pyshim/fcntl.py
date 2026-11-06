"""fcntl for the Windows build: the engine locks a folder with flock() while it
unpacks its tar (dm/tools/tree_tar.py). Windows cannot open a directory as a file,
and has no flock(); a build is serialized anyway, so the lock is a no-op. The
constants are the ones the caller passes.
"""
LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def flock(fd, operation):
    return None

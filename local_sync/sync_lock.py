"""OS lock released on process exit; shared by automatic and manual jobs."""
from contextlib import contextmanager


@contextmanager
def sync_lock(root):
    stream=(root/'sync.lock').open('a+b')
    locked=False
    try:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        try:
            import msvcrt
            try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);locked=True
            except OSError:pass
        except ImportError:
            import fcntl
            try:fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);locked=True
            except OSError:pass
        yield locked
    finally:
        stream.close()

"""Cooperative, nonblocking host lock shared by dispatch and operator recovery.

This fences cooperating workers; it is not proof that an orphaned model child or
a hostile administrator is absent. Operator process-tree verification is separate.
"""

import os
from contextlib import contextmanager
from pathlib import Path


class RuntimeBusy(ValueError):
    pass


@contextmanager
def runtime_guard(root):
    with (Path(root) / "runtime.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeBusy("runtime is active; stop dispatch before recovery") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

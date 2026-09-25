"""Advisory file lock: two benchmarks must never run concurrently on one machine.

Concurrent load is the single most common cause of irreproducible timings
(a co-running job can inflate one arm by 2x and make an A/B ratio meaningless).
The lock is advisory (``fcntl.flock``) so it only protects benches that use it --
wrap every timing script in ``with BenchLock(): ...`` or ``crbench run``.
"""
from __future__ import annotations

import errno
import json
import os
import socket
import time

try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover
    fcntl = None

DEFAULT_LOCK = os.environ.get("CRBENCH_LOCK", os.path.join(os.path.expanduser("~"), ".crbench.lock"))


class LockTimeout(RuntimeError):
    pass


class BenchLock:
    def __init__(self, path: str = DEFAULT_LOCK, timeout: float | None = None, poll: float = 0.5, label: str = ""):
        self.path = path
        self.timeout = timeout
        self.poll = poll
        self.label = label
        self._fh = None

    def acquire(self) -> "BenchLock":
        if fcntl is None:  # pragma: no cover
            raise RuntimeError("BenchLock requires POSIX fcntl")
        os.makedirs(os.path.dirname(os.path.abspath(self.path)) or ".", exist_ok=True)
        fh = open(self.path, "a+")
        start = time.monotonic()
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    fh.close()
                    raise
                if self.timeout is not None and time.monotonic() - start >= self.timeout:
                    holder = self.holder()
                    fh.close()
                    raise LockTimeout(f"bench lock {self.path} busy (holder: {holder})")
                time.sleep(self.poll)
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "since": time.time(), "label": self.label}))
        fh.flush()
        self._fh = fh
        return self

    def release(self) -> None:
        if self._fh is not None:
            try:
                self._fh.seek(0)
                self._fh.truncate()
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None

    def holder(self) -> dict | None:
        try:
            with open(self.path) as f:
                txt = f.read().strip()
            return json.loads(txt) if txt else None
        except (OSError, ValueError):
            return None

    def __enter__(self) -> "BenchLock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


if __name__ == "__main__":
    import tempfile

    p = os.path.join(tempfile.mkdtemp(), "x.lock")
    with BenchLock(p, label="self-check"):
        try:
            BenchLock(p, timeout=0.2).acquire()
        except LockTimeout:
            print("lock self-check OK (second acquirer blocked)")

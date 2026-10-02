"""Non-blocking, process-wide profile leases released by the OS on exit."""
import os
import threading


class ProfileBusyError(Exception):
    pass


def profile_lock_path(profile_path):
    """All supported HTTP, CLI and Python editors use this same canonical path."""
    return os.path.realpath(os.fspath(profile_path)) + ".lock"


class ProfileLease:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._guard = threading.Lock()
        self._file = open(path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                if os.fstat(self._file.fileno()).st_size == 0:
                    self._file.write(b"0")
                    self._file.flush()
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._file.close()
            raise ProfileBusyError("Profile already has an active request") from exc

    def release(self):
        with self._guard:
            if self._file.closed:
                return
            try:
                if os.name == "nt":
                    import msvcrt
                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            finally:
                self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.release()

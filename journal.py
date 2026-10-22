"""Single-threaded cooperative fixture journal, not a production config writer."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path

class Journal:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def locked(self, nonblocking=False):
        # Persistent sibling inode; never unlink a lock after a crash.
        fd = os.open(str(self.path)+'.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
            yield
        finally:
            os.close(fd)

    def stage(self):
        if not self.path.exists(): return None
        return json.loads(self.path.read_text())['stage']

    def transition(self, expected, desired):
        # Caller MUST hold locked() across check, transition and external effect.
        if self.stage() != expected: raise ValueError('STATE_CONFLICT')
        pending = self.path.with_name(self.path.name+'.next')
        fd = os.open(pending, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w', closefd=False) as f:
                json.dump({'stage':desired}, f); f.flush(); os.fsync(fd)
        finally: os.close(fd)
        os.replace(pending, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        # A leftover .next file after interruption deliberately blocks transitions.
        # No automatic recovery/retry of a started external effect.

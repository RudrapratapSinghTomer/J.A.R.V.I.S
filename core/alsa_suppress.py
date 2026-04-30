import os
import sys
from contextlib import contextmanager

@contextmanager
def suppress_alsa_warnings():
    """
    Temporarily redirect stderr to /dev/null at the C level
    to hide ALSA audio library warnings on Linux.
    """
    if os.name != "posix":
        yield
        return

    original_stderr_fd = None
    saved_stderr_fd = None
    try:
        # Save original stderr
        original_stderr_fd = sys.stderr.fileno()
        saved_stderr_fd = os.dup(original_stderr_fd)
        
        # Open /dev/null
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        
        # Redirect stderr to /dev/null
        os.dup2(devnull_fd, original_stderr_fd)
        os.close(devnull_fd)
        
        yield
        
    except Exception:
        # If anything fails (e.g. not on Linux), just run normally
        yield
        
    finally:
        try:
            # Restore original stderr
            if (
                saved_stderr_fd is not None
                and original_stderr_fd is not None
            ):
                os.dup2(saved_stderr_fd, original_stderr_fd)
                os.close(saved_stderr_fd)
        except Exception:
            pass

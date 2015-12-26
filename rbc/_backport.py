"""
Backports of Python functionality.

"""
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile

__all__ = ['TemporaryDirectory']

# Backported from Python 3.2.
class _TemporaryDirectoryBackport(object):
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:
        with TemporaryDirectory() as tmpdir:
            ...
    Upon exiting the context, the directory and everthing contained
    in it are removed.
    """

    # pylint: disable=redefined-builtin
    def __init__(self, suffix="", prefix="tmp", dir=None):
        self._closed = False
        self.name = None # Handle mkdtemp raising an exception
        self.name = _tempfile.mkdtemp(suffix, prefix, dir)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def cleanup(self):
        if self.name and not self._closed:
            try:
                _shutil.rmtree(self.name)
            except (TypeError, AttributeError) as ex:
                # Issue #10188: Emit a warning on stderr
                # if the directory could not be cleaned
                # up due to missing globals
                if "None" not in str(ex):
                    raise
                _sys.stderr.write("ERROR: {!r} while cleaning up {!r}\n".format(
                    ex, self,))
                return
            self._closed = True

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def __del__(self):
        self.cleanup()

# Try standard tempfile implementation in preference to backported one
try:
    TemporaryDirectory = _tempfile.TemporaryDirectory
except AttributeError:
    TemporaryDirectory = _TemporaryDirectoryBackport

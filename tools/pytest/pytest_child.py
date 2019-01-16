"""
pytest integration helper for 'testrunner'.

For the moment most the 'child' creation has been duplicated here as there
are no independant function for creating a child.
I on purpose tried to not modify the implementation in testrunner.

Logging on the console while running tests can be disabled by setting
environment variable TEST_LOG_CONSOLE=0 (default: 1)

The test timeout is extracted from either:

* a `TIMEOUT` variable
* the 'testrunner.run' timeout argument (text extracted)
* default DEFAULT_TIMEOUT copied from testrunner as it is not set in a var
"""
import os
import sys
import signal
import subprocess
import re
import time

import pexpect
import pytest
import testrunner


DEFAULT_TIMEOUT = 10
TEST_LOG_CONSOLE = bool(int(os.environ.get('TEST_LOG_CONSOLE', '1')))
TEST_TIMEOUT_ATTR = 'TIMEOUT'


class CustomSpawn(pexpect.spawn):
    """Convenient subclass to better catch pexpect timeout and eof errors.

    Catch the pexpect exceptions and replace the value wih the called pattern.
    At the same time, remove all traceback and context as we do not care about
    where in the original pexpect library.
    """

    def expect(self, pattern, *args, **kwargs):
        # pylint:disable=arguments-differ
        try:
            return super().expect(pattern, *args, **kwargs)
        except (pexpect.TIMEOUT, pexpect.EOF) as exc:
            exc.orig_value = exc.value
            exc.value = pattern
            raise exc.with_traceback(None) from None

    def expect_exact(self, pattern, *args, **kwargs):
        # pylint:disable=arguments-differ
        try:
            return super().expect_exact(pattern, *args, **kwargs)
        except (pexpect.TIMEOUT, pexpect.EOF) as exc:
            exc.orig_value = exc.value
            exc.value = pattern
            raise exc.with_traceback(None) from None


@pytest.fixture(scope="module")
def child(request, timeout=None):
    """Duplicate 'testrunner' child creation.

    This should be replaced by testrunner having an object creation function
    for this.
    """
    if timeout is None:
        timeout = _timeout(request)

    _child = CustomSpawn("make term", timeout=timeout,
                         encoding='utf-8', codec_errors='replace')

    # on many platforms, the termprog needs a short while to be ready...
    time.sleep(testrunner.MAKE_TERM_STARTED_DELAY)

    # Log either to console and capture or only captured stdout
    _child.logfile = ConsoleAndCapture() if TEST_LOG_CONSOLE else sys.stdout

    try:
        subprocess.check_output(('make', 'reset'), stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        # make reset yields error on some boards even if successful
        pass

    yield _child

    # TODO check cleanup

    print("")
    try:
        os.killpg(os.getpgid(_child.pid), signal.SIGKILL)
    except ProcessLookupError:
        print("Process already stopped")

    _child.close()


def _timeout(request, timeout_attr=TEST_TIMEOUT_ATTR, default=60):
    """Try to extract the timeout from the calling 'request' context.

    It returns the first of:
     * a `timeout_attr` attribute defined in the module
     * checking the text of the script to find `run` 'timeout=' argument
     * `default` value
    """

    timeout = getattr(request.module, timeout_attr, None)
    if timeout is not None:
        return timeout

    timeout = read_run_timeout(request.module.__file__, default=default)

    return timeout


def read_run_timeout(testfile, default=None):
    """Return the 'timeout' value from the test file.

    This is a hack to extract timeout from the test file.
    """
    run_args_re = re.compile(r'^    sys.exit\(run\([^,]+(.*)\)\)$')
    timeout_re = re.compile(r'timeout=(\d+)')

    with open(testfile) as testfd:
        for line in testfd:
            args_match = run_args_re.match(line)
            if not args_match:
                continue
            run_args = args_match.group(1)

            # Found the 'run' function and arguments

            timeout_match = timeout_re.search(run_args)
            if not timeout_match:
                return default
            timeout = timeout_match.group(1)

            return int(timeout)

    raise ValueError("Could not extract 'timeout'")


class ConsoleAndCapture():
    """Write both to Console (__stdout__) and Capture (stdout)."""
    @staticmethod
    def write(data):
        """Write data to outputs."""
        sys.stdout.write(data)
        sys.__stdout__.write(data)

    @staticmethod
    def flush():
        """Flush outputs."""
        sys.stdout.flush()
        sys.__stdout__.flush()

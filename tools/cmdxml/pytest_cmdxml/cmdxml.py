"""Hardwritten 'test' file for 'cmdxml'"""

import tempfile
import subprocess

# TODO: I think this should be configurable
BASH_OPT = '-xe'


def test_command(command):
    """Execute given test command."""
    assert _execute_command(command) == 0


def test_script(script):
    """Execute given script."""
    assert _execute_script(script) == 0


def _execute_command(command):
    with tempfile.NamedTemporaryFile('w+') as script:
        script.write(command)
        script.flush()
        return _execute_script(script.name)


def _execute_script(path):
    return subprocess.call(['bash', BASH_OPT, path])

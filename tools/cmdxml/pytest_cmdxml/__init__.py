"""
Define command line options and associated fixtures.
This allows triggering tests based on the command line provided options.
"""

import os

__version__ = '0.1.0'

CURDIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILE = os.path.join(CURDIR, 'cmdxml.py')
PYTEST_ARGS = [TEST_FILE]

FIXTURES = ('command', 'script')


def pytest_addoption(parser):
    """Define options to configure the fixtures.

    The 'metavar' matches the fixture name.
    """
    parser.addoption('--command', default=[], action="append",
                     metavar='command',
                     help='Command to test, can be specified multiple times')
    parser.addoption('--script', default=[], action="append",
                     metavar='script',
                     help='Script to test, can be specified multiple times')


def pytest_generate_tests(metafunc):
    """Generate parametrized tests based on the fixtures options."""
    for option in FIXTURES:
        if option in metafunc.fixturenames:
            metafunc.parametrize(option, metafunc.config.getoption(option))


def pytest_collection_modifyitems(config, items):
    """Deselect tests without fixtures to remove the 'skip' in the output."""
    selected, deselected = _filter_empty_fixtures(config, items)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected


def _filter_empty_fixtures(config, items):
    """Remove items which use an empty option. Name matches fixture name.

    # https://pythontesting.net/framework/pytest/
    #     pytest-run-tests-using-particular-fixture/

    :returns: selected, deselected
    """
    selected = []
    deselected = []
    disabled_fixtures = {f for f in FIXTURES if not getattr(config.option, f)}
    for item in items:
        if disabled_fixtures & set(getattr(item, 'fixturenames', ())):
            deselected.append(item)
        else:
            selected.append(item)
    return selected, deselected

#! /usr/bin/env python3
"""pytest_cmdxml setuptools script."""

import os
from setuptools import setup


def get_version(package):
    """ Extract package version without importing file
    Importing cause issues with coverage,
        (modules can be removed from sys.modules to prevent this)
    Importing __init__.py triggers importing rest and then requests too

    Inspired from pep8 setup.py
    """
    with open(os.path.join(package, '__init__.py')) as init_fd:
        for line in init_fd:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])  # pylint:disable=eval-used
    return ''


SCRIPTS = ['cmdxml']
PACKAGE = 'pytest_cmdxml'


setup(
    name=PACKAGE,
    version=get_version(PACKAGE),
    packages=[PACKAGE],
    author='Gaëtan Harter',
    author_email='gaetan.harter@fu-berlin.de',
    scripts=SCRIPTS,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha'
        'Environment :: Console',
        'Framework :: Pytest',
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=['pytest'],
    python_requires='>=3.0.*',
)

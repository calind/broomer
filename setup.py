# -*- coding: utf-8 -*-
# vim: ft=python:sw=4:ts=4:sts=4:et:
# pylint: skip-file
import sys

from setuptools import setup

from broomer import (__version__ as version,
                     __description__ as description)

install_requires = ['zipa', 'maya', 'PyYAML', 'pystache']
tests_require = ['pytest-runner>=2.0,<3dev', 'pytest', 'pytest-pylint']
setup_requires = []

if {'pytest', 'test', 'ptr'}.intersection(sys.argv):
    setup_requires = setup_requires + ['pytest-runner>=2.0,<3dev',
                                       'pytest-pylint']

setup(
    name='broomer',
    version=version,
    description=description,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require
    },
    entry_points={
        'console_scripts': [
            'broomer = broomer.cli:main'
        ]
    },
)

"""
Setup configuration for installation via pip, easy_install, etc.

"""
import sys
from setuptools import setup, find_packages

# Python 3.4+ comes with enum.Enum. For prior Pythons, we can install the enum34
# package from PyPI.
if sys.hexversion < 0x030400F0:
    enum_requires = ['enum34']
else:
    enum_requires = []

# The find_packages function does a lot of the heavy lifting for us w.r.t.
# discovering any Python packages we ship.
setup(
    name='rbc',
    version='0.0.1dev',
    packages=find_packages(),

    # PyPI packages required for the *installation* and usual running of the
    # tools.
    install_requires=[
        'docopt',
        'future',
        'grako',
        'llvmlite',
        'whichcraft',
    ] + enum_requires,

    entry_points={
        'console_scripts': [
            'rbc=rbc:main',
        ],
    },

    package_data = {
        'rbc': ['*.c'],
    },
)

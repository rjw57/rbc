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
    version='0.1.0a',
    description='Example B compiler written with LLVM',
    url='https://github.com/rjw57/rbc',
    author='Rich Wareham',
    author_email='rich.rbc@richwareham.com',
    license='MIT',
    packages=find_packages(),

    # PyPI packages required for the *installation* and usual running of the
    # tools.
    install_requires=[
        'docopt',
        'future',
        'grako',
        'llvmlite<0.9.0',
        'whichcraft',
    ] + enum_requires,

    entry_points={
        'console_scripts': [
            'rbc=rbc:main',
        ],
    },

    package_data={
        'rbc': ['*.c', '*.b'],
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Compilers',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    keywords='compiler B llvm example',
)

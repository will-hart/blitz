from distutils.core import setup

setup(
    name='blitz',
    version='1.0',
    packages=['blitz', 'blitz.io', 'blitz.web', 'blitz.data', 'blitz.test'],
    url='http://www.blitzlogger.com',
    license='GPL v3.0',
    author='William Hart',
    author_email='will@blitzlogger.com',
    description='A modular data logger',
    requires=['redis', 'bitstring', 'blinker', 'numpy', 'sqlalchemy', 'tornado']
)

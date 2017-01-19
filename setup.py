import sys
import versioneer
from setuptools import setup

from broomer import (__version__ as version,
                     __description__ as description)


try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except ImportError as e:
    long_description = open('README.md').read()
except OSError as e:
    print(e)
    sys.exit(1)

install_requires = ['zipa', 'maya', 'PyYAML', 'pystache']
tests_require = ['pytest', 'pytest-runner>=2.0,<3dev', 'pytest-flake8']
setup_requires = tests_require + ['pypandoc']

setup(
    name='broomer',
    version=version,
    description=description,
    author="Calin Don",
    author_email="calin.don@gmail.com",
    url="https://github.com/calind/broomer",
    long_description=long_description,
    cmdclass=versioneer.get_cmdclass(),
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
    license='BSD',
    keywords='github issues broomer',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)

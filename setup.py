from setuptools import find_packages, setup

with open('README.rst', 'r') as f:
    readme = f.read()

setup(
    name='cueillette',
    packages=find_packages(exclude=['docs', 'tests*']),
    version='0.1.0',
    description=(
        'A toolbox to get rid of those fucking proprietary web APIs.'
    ),
    long_description=readme,
    author='Guillaume Paulet',
    author_email='guillaume.paulet@giome.fr',
    license='Public Domain',
    install_requires=[
        'lxml',
        'requests',
        'ujson',
    ],
)

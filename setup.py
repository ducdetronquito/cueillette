from setuptools import find_packages, setup

with open('README.rst', 'r') as f:
    readme = f.read()

setup(
    name='cueillette',
    packages=find_packages(exclude=['docs', 'tests*']),
    version='0.1.0',
    description=(
        "Access content from websites who have a fucking proprietary API,"
        " or websites who haven't any. 🖕"
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

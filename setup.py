from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

setup(
    name = "open511",
    version = "0.1",
    url='',
    license = "",
    packages = [
        'open511',
    ],
    install_requires = [
        'lxml',
    ]
)

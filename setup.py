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
        'lxml>=2.3',
        'WebOb>=1.2,<2',
        'python-dateutil>=1.5,<2.0',
        'requests>=1.2,<2',
        'pytz>=2013b',
        'django-appconf==0.5',
        'cssselect==0.8',
    ],
    entry_points = {
        'console_scripts': [
            'mtl_kml_to_open511 = open511.scripts.mtl_kml_to_open511:main',
            'scrape_mtq_to_open511 = open511.scripts.scrape_mtq_to_open511:main',
        ]
    },
)

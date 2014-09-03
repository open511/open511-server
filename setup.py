from setuptools import setup, find_packages

setup(
    name = "open511-server",
    version = "0.1",
    url='',
    license = "",
    packages = find_packages(),
    dependency_links = [
        'https://www.github.com/opennorth/open511/archive/master.zip#egg=open511-0.3',
    ],
    install_requires = [
        'open511>=0.3',
        'lxml>=2.3',
        'WebOb>=1.2,<2',
        'python-dateutil>=1.5,<2.0',
        'requests>=1.2,<2',
        'pytz>=2013b',
        'django-appconf==0.5',
        'cssselect==0.8',
        'Django>=1.7,<1.8'
    ],
)

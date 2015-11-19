from setuptools import setup, find_packages

setup(
    name = "open511-server",
    version = "0.1",
    url='',
    license = "",
    packages = find_packages(),
    dependency_links = [
        'https://www.github.com/open511/open511/archive/master.zip#egg=open511-0.3',
    ],
    install_requires = [
        'open511>=0.5',
        'lxml>=2.3',
        'WebOb==1.5.1',
        'python-dateutil==2.4.2',
        'requests==2.8.1',
        'pytz>=2015b',
        'django-appconf==1.0.1',
        'cssselect==0.8',
        'Django==1.9rc1',
    ],
)

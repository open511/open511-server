from setuptools import setup, find_packages

setup(
    name = "open511-server",
    version = "0.1",
    url='',
    license = "",
    packages = find_packages(),
    install_requires = [
        'open511==0.5',
        'lxml>=3.0,<=4.0',
        'WebOb==1.5.1',
        'python-dateutil==2.4.2',
        'requests==2.8.1',
        'pytz>=2015b',
        'django-appconf==1.0.1',
        'cssselect==0.9.1',
        'Django>=1.10.1,<=1.10.99',
        'jsonfield==1.0.3'
    ],
    entry_points = {
        'console_scripts': [
            'open511-task-runner = open511_server.task_runner:task_runner'
        ]
    },
)

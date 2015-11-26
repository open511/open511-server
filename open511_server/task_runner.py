import gevent
import gevent.monkey
gevent.monkey.patch_all()

from copy import copy
from functools import partial
import logging
import logging.config

import django
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

DEFAULT_TASK_OPTS = {
    'INTERVAL': 600,
    'TIMEOUT': 120,
    'IMPORTER': 'open511_server.importer.Open511Importer'
}

def run_task(task_def):
    logger.debug("Running task %r" % task_def)
    importer_class = import_string(task_def['IMPORTER'])
    importer = importer_class(task_def, persist_status=True)

    timeout = gevent.Timeout(task_def['TIMEOUT'])
    try:
        importer.run()
    except Exception as e:
        logger.exception("{} running task {}".format(e.__class__.__name__, importer.id))
    finally:
        timeout.cancel()

def spawn_task(task_def):
    greenlet = gevent.spawn(run_task, task_def)
    greenlet.link(partial(task_complete, task_def))

def task_complete(task_def, greenlet):
    if greenlet.exception:
        logger.error("{} running task {}: e".format(greenlet.exception.__class__.__name__, task_def.get('URL'),
            greenlet.exception))
    gevent.sleep(task_def['INTERVAL'])
    spawn_task(task_def)

def run_forever():
    while True:
        gevent.sleep(120)

def task_runner():
    django.setup()
    task_defs = getattr(settings, 'OPEN511_IMPORT_TASKS', None)
    if not task_defs:
        raise Exception("No tasks defined in settings.OPEN511_IMPORT_TASKS")

    for task_def in task_defs:
        td = copy(DEFAULT_TASK_OPTS)
        td.update(task_def)
        spawn_task(td)

    gevent.spawn(run_forever).join()

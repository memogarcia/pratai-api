# TODO(m3m0): this should be decoupled from the api. maybe the scheduler?

import logging

from models import Function, Log, Daemon, Runtime


log = logging.getLogger('pratai')


def create_mappings():
    log.info('Creating mappings')
    Function.init()
    Log.init()
    Daemon.init()
    Runtime.init()


if __name__ == '__main__':
    create_mappings()

import logging

from config import parse_config


def prepare_log():
    logger = logging.getLogger('pratai')
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(parse_config("logging")['path'])
    handler.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

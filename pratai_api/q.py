# -*- coding: utf-8 -*-

"""
pratai_api.q
~~~~~~~~~~~~
This module contains a function that will send a request to the message
pipeline
"""

import logging

import zmq

from config import parse_config


log = logging.getLogger('pratai')

endpoint = parse_config("queue")['endpoint']


def send(action, function_id=None, payload=None, request_id=None):
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(endpoint)

    try:

        message = {
            'action': action,
            'payload': payload,
            'request_id': request_id,
            'function_id': function_id
        }
        sender.send_json(message)

    except Exception as error:
        log.error('Error pushing message to queue {} with error {}.'.format(
            request_id, error))

    finally:
        sender.close()

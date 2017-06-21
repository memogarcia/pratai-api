import logging
import uuid

from flask import Flask, Response, jsonify, request

from elasticsearch.exceptions import NotFoundError

import utils
from config import parse_config
import models
from log import prepare_log
import q


prepare_log()
log = logging.getLogger('pratai')

driver = parse_config("driver")['driver']
driver_endpoint = parse_config("driver")['driver_endpoint']


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = parse_config("payload")['max_size']


@app.before_request
def keystone():
    # return unauthorized()
    # once this is allowed, we still to validate the access to individual
    # resources in each function
    if request.endpoint == 'function_execute':
        # print('skip validation?')
        pass
    else:
        # this should be replaced by keystone middleware
        #if not request.headers.get('X-User-ID', None) \
        #        and not request.headers.get('X-Tenant-ID'):
        #    return unauthorized()
        pass


@app.errorhandler(400)
def bad_request(error=""):
    message = {
            'status_code': 400,
            'message': 'Bad Request: {0}'.format(error),
    }
    log.error(error)
    resp = jsonify(message)
    resp.status_code = 400
    return resp


@app.errorhandler(404)
def not_found(error=""):
    message = {
            'status_code': 404,
            'message': 'Not Found: ' + request.url,
    }
    log.error(error)
    resp = jsonify(message)
    resp.status_code = 404
    return resp


@app.errorhandler(401)
def unauthorized(error=""):
    message = {
            'status_code': 401,
            'message': 'Unauthorized',
    }
    log.error(error)
    resp = jsonify(message)
    resp.status_code = 401
    return resp


@app.errorhandler(405)
def method_not_allowed(error=""):
    message = {
            'status_code': 405,
            'message': 'Method Not Allowed',
    }
    log.error(error)
    resp = jsonify(message)
    resp.status_code = 405
    return resp


@app.errorhandler(500)
def critical_error(error=""):
    message = {
            'status_code': 500,
            'message': error,
    }
    log.error(error)
    resp = jsonify(message)
    resp.status_code = 500
    return resp


@app.route('/', methods=['GET'])
def discovery():
    endpoints = {}
    return jsonify(endpoints)


@app.route('/functions', methods=['GET'])
def function_list():
    bs = models.FunctionSearch()
    response = bs.execute()
    functions = [hit.to_dict() for hit in response]

    resp = jsonify(functions)
    resp.status_code = 302
    return resp


@app.route('/functions/<function_id>', methods=['GET'])
def function_get(function_id):
    # TODO(m3m0): filter by user and tenant as well, or should it be in the middleware?
    try:
        f = models.Function.get(id=function_id)
    except NotFoundError:
        return not_found()
    else:
        resp = jsonify(f.to_dict())
        resp.status_code = 302
        return resp


@app.route('/functions', methods=['POST'])
def function_create():
    with utils.AtomicRequest() as atomic:

        function_id = uuid.uuid4().hex

        atomic.driver_endpoint = driver_endpoint

        user, tenant = utils.get_headers(request)

        zip_file = utils.get_zip(request)
        zip_url = utils.upload_zip(function_id, zip_file)

        if not zip_url:
            atomic.errors = True
            return critical_error('Not able to store zip.')

        atomic.zip_url = zip_url

        metadata = utils.get_metadata(request)

        if not utils.validate_json(utils.build_schema, metadata):
            atomic.errors = True
            return bad_request("Error validating json.")

        tag = "{0}_{1}_{2}".format(tenant, user, metadata.get('name'))
        payload = {
            "memory": metadata.get('memory'),
            "tags": [tag],
            "runtime": metadata.get('runtime'),
            "zip_location": zip_url,
            "name": metadata.get('name')
        }

        image_id = utils.create_image(driver_endpoint, payload)
        atomic.image_id = image_id

        function = utils.create_function(tenant, user, function_id, image_id, zip_url, tag, metadata)

        if not function:
            atomic.errors = True
            return critical_error('Error building the function.')

        return Response(function_id, status=201)


@app.route('/functions/<function_id>', methods=['DELETE'])
def function_delete(function_id):
    """Delete the container image which contains the function
    :param function_id:
    :return:
    """
    try:
        f = models.Function.get(id=function_id)
    except NotFoundError:
        return not_found()
    utils.delete_image(f.image_id, driver_endpoint)
    utils.delete_function(function_id)
    return Response(status=204)


@app.route('/functions/<function_id>', methods=['POST'])
def function_execute(function_id):
    request_id = uuid.uuid4().hex
    cleaned_data = utils.clean(request.data)
    q.send('run',
           function_id=function_id,
           payload=cleaned_data,
           request_id=request_id)
    return Response(request_id, status=202)


@app.route('/functions/<function_id>', methods=['POST'])
def function_stop(function_id):
    utils.stop_function(function_id, driver_endpoint)
    return Response(status=200)


@app.route('/runtimes', methods=['GET'])
def runtime_list():
    # this will be dynamic, meaning that a user can build its own runtimes.
    # by sending a json describing the os, dependencies, etc.
    runtimes = []
    resp = jsonify(runtimes)
    resp.status_code = 302
    return resp


@app.route('/events', methods=['GET'])
def event_list():
    return jsonify(['webhook', 'wait_for_response'])


@app.route('/status', methods=['GET'])
def status():
    # query the cluster endpoint in the db.
    return 'ok'


if __name__ == '__main__':
    app.run(host=parse_config("server")['url'],
            port=int(parse_config("server")['port']),
            debug=True)

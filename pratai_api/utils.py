import json
import os
import time
import logging

from StringIO import StringIO

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from elasticsearch.exceptions import NotFoundError

import requests

from models import Function
from config import parse_config


endpoint = '{0}://{1}:{2}'.format(
    parse_config("server")['protocol'],
    parse_config("server")['url'],
    parse_config("server")['port']
)

log = logging.getLogger('pratai')

access_key = os.environ.get('AWS_ACCESS_KEY')
secret_key = os.environ.get('AWS_SECRET_KEY')

conn = S3Connection(access_key, secret_key)

b = conn.get_bucket('pratai')
k = Key(b)


def make_request(method, url, headers=None, data=None, retries=3):
    """ make a request, with the ability to have retries in specific return
    codes
    :param method: HTTP verb method
    :param url:
    :param retries: int, this should be greater or equal than 1
    :return:
    """
    no_retry_status = [404, 401, 403]
    may_retry_status = [408, 500, 502, 503]

    if not retries:
        return requests.request(method=method,
                                url=url,
                                headers=headers,
                                data=data)

    while retries:
        r = requests.request(method=method,
                             url=url,
                             headers=headers,
                             data=data)
        if r.status_code in no_retry_status:
            return r

        elif r.status_code in may_retry_status:
            retries -= 1
            time.sleep(1)

            if retries == 0:
                return r
            continue

        else:
            return r


def get_metadata(req):
    metadata = StringIO()
    f1 = req.files['metadata']
    metadata.write(f1.read())
    return json.loads(metadata.getvalue())


def get_zip(req):
    zip_file = StringIO()
    f = req.files['zip_file']
    zip_file.write(f.read())
    return zip_file.getvalue()


def upload_zip(function_id, zip_file):
    try:
        k.key = "{0}.zip".format(function_id)
        k.set_contents_from_string(zip_file)
        k.set_acl('public-read')
        url = k.generate_url(expires_in=0, query_auth=False, force_http=True)
        return url
    except Exception as error:
        log.error(error.message)
        return None


def delete_zip(key):
    k.key = key
    return k.delete()


def create_function(tenant_id, user_id, function_id, image_id, zip_url, tag, meta=None):
    try:
        f = Function()
        f.meta.id = function_id  # make this an uuid
        f.function_id = function_id  # make this an uuid
        f.user_id = user_id
        f.tenant_id = tenant_id
        f.image_id = image_id
        f.zip_location = zip_url
        f.type = 'async'
        f.event = 'webhook'
        f.description = meta.get('description', None)
        f.memory = meta.get('memory', None)
        f.name = meta.get('name', None)
        f.runtime = meta.get('runtime', None)
        f.endpoint = "{0}/functions/{1}".format(endpoint, function_id)
        f.tag = tag
        return f.save()
    except Exception as error:
        log.error(error.message)
        return None


def delete_function(function_id):
    try:
        f = Function.get(id=function_id)
    except NotFoundError as error:
        log.error(error.message)
        return 404
    else:
        zip_file = f.zip_location[-36:]
        delete_zip(zip_file)
        f.delete()


def get_headers(req):
    """
    validate that request headers contains user and tenant id
    :param req: global request
    :return: user and tenant id as strings
    """
    user = req.headers.get('X-User-ID', None)
    tenant = req.headers.get('X-Tenant-ID', None)
    return user, tenant


def validate_json(schema, doc):
    """
    Validate that a json doesn't contains more elements that it should, raise
    in case it does.
    :return:
    """
    is_invalid = set(doc).difference(set(schema))
    if is_invalid:
        return False
    return True


build_schema = ['name', 'description', 'event', 'runtime', 'publish',
                'memory', 'type']


def delete_image(image_id, driver_endpoint):
    url = '{0}/images/{1}'.format(driver_endpoint, image_id)
    return make_request('DELETE', url)


def create_image(driver_endpoint, payload):
    url = '{0}/images/build'.format(driver_endpoint)
    r = make_request('POST', url, data=json.dumps(payload))

    return r.json()['image_id']


def stop_function(function_id, driver_endpoint):
    url = '{0}/functions/{1}/stop'.format(driver_endpoint, function_id)
    r = make_request('POST', url)
    return r


class AtomicRequest(object):
    """context manager to make sure that all actions are completed atomically,
    if not, clean

    scenario 1:
        creating a function involves 3 steps:
            upload zip
            create container
            save to db

    scenario 2
        deleting a function involves 3 steps:
            delete the zip
            delete the container
            delete the db entry
    """

    def __init__(self):
        self.driver_endpoint = None
        self.errors = False
        self.zip_url = None
        self.image_id = None
        self.function_id = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.errors:
            self.clean()

    def clean(self):
        log.info("Cleaning")
        # TODO (m3m0): cleaning is not removing the zip file
        # when the driver fails to respond
        try:
            delete_zip(self.zip_url[-36:])
        except Exception as error:
            log.error(error.message)

        try:
            delete_image(self.image_id, self.driver_endpoint)
        except Exception as error:
            log.error(error.message)

        try:
            delete_function(self.function_id)
        except Exception as error:
            log.error(error.message)


def clean(request_data):
    data = json.loads(request_data)
    cleaned_data = {
        'payload': data['payload']
    }
    return cleaned_data

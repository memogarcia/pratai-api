from elasticsearch_dsl import DocType, String, Boolean, Long, FacetedSearch, Date
from elasticsearch_dsl.connections import connections

from config import parse_config

connections.create_connection(hosts=[parse_config("db")['url']])


class Function(DocType):
    function_id = String(index='not_analyzed')
    tenant_id = String(index='not_analyzed')
    user_id = String(index='not_analyzed')
    image_id = String(index='not_analyzed')
    name = String(index='not_analyzed')
    description = String(index='not_analyzed')
    type = String(index='not_analyzed')
    event = String(index='not_analyzed')
    public = Boolean()
    endpoint = String(index='not_analyzed')
    runtime = String(index='not_analyzed')
    memory = Long()
    zip_location = String(index='not_analyzed')
    tags = String()
    status = String(index='not_analyzed')

    class Meta:
        index = 'pratai'


class FunctionSearch(FacetedSearch):
    doc_types = [Function, ]
    # fields that should be searched
    fields = ['function_id', 'tenant_id', 'user_id', 'image_id', 'name',
              'description', 'type', 'public', 'endpoint', 'runtime',
              'zip_location', 'tags']


class Log(DocType):
    function_id = String(index='not_analyzed')
    tenant_id = String(index='not_analyzed')
    user_id = String(index='not_analyzed')
    image_id = String(index='not_analyzed')
    logs = String()

    class Meta:
        index = 'pratai'


class LogSearch(FacetedSearch):
    doc_types = [Function, ]
    # fields that should be searched
    fields = ['function_id', 'tenant_id', 'user_id', 'image_id', 'logs']


class Daemon(DocType):
    """Useful to keep track of the cluster of daemons"""
    daemon_id = String(index='not_analyzed')
    daemon_type = String(index='not_analyzed')
    status = String(index='not_analyzed')
    joined_at = Date()

    class Meta:
        index = 'pratai'


class Runtime(DocType):
    runtime_id = String(index='not_analyzed')
    name = String(index='not_analyzed')
    description = String(index='not_analyzed')

    class Meta:
        index = 'pratai'

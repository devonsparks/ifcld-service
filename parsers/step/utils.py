from urllib import request
from rdflib import Graph
import json

class Client:

    def begin_file(self, file, offset):
        pass

    def end_file(self, file, offset):
        pass

    def begin_section(self, section, offset):
        pass
    
    def end_section(self, section, offset):
        pass

    def begin_entity(self, entity, offset):
        pass

    def end_entity(self, entity, offset):
        pass
    
    def begin_parameter(self, param, offset):
        pass

    def end_parameter(self, param, offset):
        pass


def get_schema_graph(schema_name):
    with request.urlopen("http://ifc-ld.org/schemas/{schema_name}.ttl".format(schema_name=schema_name)) as response:
        return Graph().parse(data=response.read())


def get_offset_map(schema_name):
    with request.urlopen("http://ifc-ld.org/schemas/{schema_name}.offsets.json".format(schema_name=schema_name)) as response:
        return json.loads(response.read())
    

def get_ordered_attribute_set(schema_name):
    with request.urlopen("http://ifc-ld.org/schemas/{schema_name}.ordered.json".format(schema_name=schema_name)) as response:
        return json.loads(response.read())

def inline_document_loader(doc, options={}):
    return {"contentType": "application/json",
            "document": doc,
            "contextUrl": None,
            "documentUrl": None}


# Standard Library
from pathlib import Path
from urllib.parse import quote as urlquote
from json import dumps, loads
from sys import stdout
from dateutil import parser as dtparser

# External Depedencies
from SCL.Part21 import Parser, TypedParameter

# Internal Dependencies
from utils.common import doc
from utils.parsing.client import IClient
from utils.parsing.visitors import FileVisitor
import utils.guid as guid

from rdflib import ConjunctiveGraph, URIRef, BNode, Literal, Namespace, RDF, RDFS, XSD, PROV
from rdflib.graph import Collection

def is_enum(param):
    return isinstance(param, str) and param.startswith('.') and param.endswith('.')

def is_ref(param):
    return isinstance(param, str) and param.startswith('#') and param[1:].isdigit()

def is_null(param):
    return param == "$"

def is_derivable(param):
    return param == "*"

def is_collection(param):
    return isinstance(param, list)

def is_string(param):
    return isinstance(param, str)

def is_number(param):
    return isinstance(param, int) or isinstance(param, float)

def is_float(param):
    return isinstance(param, float)

def is_int(param):
    return isinstance(param, int)

def is_boolean(param):
    return is_enum(param) and param in [".T.", ".F."]

def is_ifcguid(param):
    return isinstance(param, str) and len(param) == 22 and all(ch in guid.chars for ch in param)

def is_terminal(param):
    return is_int(param) or is_float(param) or is_string(param) or is_enum(param)

def is_typed_parameter(param):
    return isinstance(param, TypedParameter)

def make_terminal(client, param):
    assert is_terminal(param)
    if is_ref(param):
        return URIRef(param)
    if is_boolean(param):
        if param == ".T.":
            return Literal(True, datatype = XSD.boolean)
        elif param == ".F.":
            return Literal(False, datatype = XSD.boolean)
        else:
            raise Exception("Should not happen")
    elif is_enum(param):
        return Literal(param.lower()[1:-1], datatype = XSD.string)
    elif is_string(param):
        return Literal(param.lower(), datatype = XSD.string)
    elif is_float(param):
        return Literal(float(param), datatype = XSD.decimal)
    elif is_int(param):
        return Literal(int(param), datatype = XSD.integer)
    else:
        raise Exception("Unknown literal type")


def make_list(client, lst):
    head = BNode()
    coll = Collection(client.graph, head)
    for item in lst:
        coll.append(make_value(client, item))
    return head

def make_typed_parameter(client, param):
    head = BNode()
    client.graph.add((head, RDF.value, make_value(client, param.params), client.graph.identifier))
    client.graph.add((head, RDF.type, URIRef(param.type_name.lower()), client.graph.identifier))
    return head

def make_value(client, param):
    if is_terminal(param):
        return make_terminal(client, param)
    elif is_collection(param):
        return make_list(client, param)
    elif is_typed_parameter(param):
        if len(param.params) > 1 or len(param.params) == 1 and is_collection(param.params[0]):
            return make_value(client, param.params)
        else:
            return make_value(client, param.params[0])
    else:
        raise Exception("Should not happen")


class IFCLDClient(IClient):
    def __init__(self, **options):
        self.graph = None
        self.current_entity = None
        self.current_parameter = None
        self.vocab_uri = None
        self.base_uri = None

    def beginFile(self, file, offset):
        self.graph = ConjunctiveGraph(identifier = "http://base.com/guid#")
        self.base_uri = self.graph.identifier
        self.vocab_uri = "http://ifc-ld.org/{ifc_schema}/".format(ifc_schema=file.header.file_schema.params[0][0].lower())
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.bind("ifc", Namespace(self.vocab_uri))
        self._add_provenance(file)


    def _add_provenance(self, file):
        self.graph.add((self.graph.identifier, PROV.generatedAtTime, 
                    Literal(dtparser.parse(file.header.file_name.params[1]).isoformat(), datatype=XSD.dateTime), self.graph.identifier))
        self.graph.add((self.graph.identifier, PROV.wasAttributedTo, 
                    Literal(file.header.file_name.params[3][0], datatype=XSD.string), self.graph.identifier))
    
    def beginEntity(self, entity, offset):
        self.current_entity = entity
        self.graph.add((URIRef(entity.ref, base=self.base_uri), RDF.type, URIRef(entity.type_name.lower(), base=self.vocab_uri), self.graph.identifier))

    def beginParameter(self, param, offset):
        self.current_parameter = param
        if not (is_null(param) or is_derivable(param)):
            predicate = URIRef("param-{offset}".format(offset=offset), base=self.vocab_uri)
            self._add_statement(predicate)

    def _add_statement(self, predicate):
        param = self.current_parameter
        entity = self.current_entity.ref
        if is_ref(param):
            self.graph.add((URIRef(entity, base=self.base_uri), predicate, URIRef(param, base=self.graph.identifier), self.graph.identifier))
        else:  
            value_node = BNode()
            self.graph.add((URIRef(entity, base=self.base_uri), predicate, value_node, self.graph.identifier))
            self.graph.add((value_node, RDF.value, make_value(self, param), self.graph.identifier))
            if is_typed_parameter(param):
                self.graph.add((value_node, RDF.type, URIRef(param.type_name.lower(), base=self.vocab_uri), self.graph.identifier))

    def endFile(self, file, offset):
        pass

    def endEntity(self, entity, offset):
        self.current_entity = None

    def endParameter(self, param, offset):
        self.current_parameter = None

class MalformedInputError(ValueError):
    pass


def parse(stream):
    parser = Parser()
    try:
        return parser.parse(stream.read())
    except:
        raise MalformedInputError("Unable to parse input.")


def ast_to_client(ast):
    client = IFCLDClient()
    FileVisitor().visit(client, ast)
    return client
    
def stp_to_ifcld(input_stream, output_stream = stdout, output_format = "turtle"):
    ast = parse(input_stream)
    client = ast_to_client(ast)
    output_stream.write(client.graph.serialize(format=output_format))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Convert a STEP Part 21 file to IFC-LD')
    parser.add_argument('-f', '--file', dest='file', 
                        default=0, help='STEP Part 21 input file')
    parser.add_argument('-s', '--serialization', dest='serialization')
    parser.set_defaults(serialization="turtle")
    args = parser.parse_args()
    with open(args.file) as input_stream:
        stp_to_ifcld(input_stream, output_format=args.serialization)

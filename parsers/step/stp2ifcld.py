# Standard Library
from pathlib import Path
from urllib.parse import quote as urlquote
from sys import stdout


# External Depedencies
from SCL.Part21 import Parser, TypedParameter
from rdflib import ConjunctiveGraph, URIRef, BNode, Literal, Namespace, RDF, RDFS, XSD, PROV
from rdflib.graph import Collection
from dateutil import parser as dtparser

# Internal Dependencies
from utils import Client, get_offset_map, get_ordered_attribute_set
from visitors import FileVisitor
from errors import MalformedInputError, ImpossibleConditionError

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

def is_terminal(param):
    return is_int(param) or is_float(param) or is_string(param) or is_enum(param)

def is_typed_parameter(param):
    return isinstance(param, TypedParameter)

def make_terminal(client, param):
    assert is_terminal(param)
    if is_ref(param):
        return URIRef(param, base=client.base_uri)
    if is_boolean(param):
        if param == ".T.":
            return Literal(True, datatype = XSD.boolean)
        elif param == ".F.":
            return Literal(False, datatype = XSD.boolean)
        else:
            raise ImpossibleConditionError("Found a logical constant ({}) that appears to be neither true nor false".format(param))
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
        coll.append(make_object(client, item))
    return head


def make_structured_value(client, param):
    head = BNode()
    client.graph.add((head, RDF.value, make_terminal(client, param), client.graph.identifier))
    if is_typed_parameter(param):
        client.graph.add((head, RDF.type, URIRef(param.type_name.lower()), client.graph.identifier))
    return head


def make_object(client, param):
    if is_ref(param):
        return URIRef(param, base=client.base_uri)
    elif is_terminal(param):
        return make_structured_value(client, param)
    elif is_collection(param):
            return make_list(client, param)
    elif is_typed_parameter(param):
        if len(param.params) > 1 or (len(param.params) == 1 and is_collection(param.params[0])):
            return make_object(client, param.params)
        else:
            return make_object(client, param.params[0])
    else:
        raise ImpossibleConditionError("An unknown value type was found")




class IFCLDClient(Client):
    def __init__(self, graph):
        self.graph = graph
        self.current_entity = None
        self.current_parameter = None        
        self.vocab_uri = None
        self.base_uri = None
        self.offset_map = None                  # maps parameter offsets to field names - derived from schema
        self.ordered_attribute_set = None       # identifies which parameters are ordered - derived from schema

    def begin_file(self, file, offset):
        schema_name = file.header.file_schema.params[0][0].lower()
        self.base_uri = "http://base.com/guid"
        self.vocab_uri = "http://ifc-ld.org/schemas/{ifc_schema}".format(ifc_schema=schema_name)

        #self.graph = ConjunctiveGraph(identifier = self.base_uri)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.bind("ifc", Namespace(self.vocab_uri+"#"))

        self.offset_map = get_offset_map(schema_name)
        self.ordered_attribute_set = get_ordered_attribute_set(schema_name)

        self._add_time_provenance(file)
        self._add_authorship_provenance(file)

    def begin_entity(self, entity, offset):
        self.current_entity = entity
        self.current_entity_type_uri = str(URIRef("#"+entity.type_name.lower(), base=self.vocab_uri))
        self.graph.add((URIRef(entity.ref, base=self.base_uri), RDF.type, URIRef(self.current_entity_type_uri), self.graph.identifier))

    def end_entity(self, entity, offset):
        self.current_entity = None
        self.current_entity_type_uri = None
    
    def begin_parameter(self, param, offset):
        if is_null(param) or is_derivable(param):
            return
        
        if self.current_entity_type_uri not in self.offset_map:
            raise Exception("Entity type {uri} not found in offset map".format(uri=self.current_entity_type_uri))
        
        property = URIRef("{property_uri}".format(property_uri=self.offset_map[self.current_entity_type_uri][offset]))
        
        if is_collection(param) and str(property) not in self.ordered_attribute_set: # sets
            for item in param:
                self.graph.add((URIRef(self.current_entity.ref, base=self.base_uri), 
                        property, make_object(self, item), self.graph.identifier))
        else:
            self.graph.add((URIRef(self.current_entity.ref, base=self.base_uri),     # lists and everything else
                        property, make_object(self, param), self.graph.identifier))
            
    def _add_time_provenance(self, file):
        print(type(self.graph))
        datetime = file.header.file_name.params[1]
        if datetime:
            self.graph.add((self.graph.identifier, 
                            PROV.generatedAtTime, 
                            Literal(dtparser.parse(datetime).isoformat(), datatype=XSD.dateTime), 
                            self.graph.identifier))
            
    def _add_authorship_provenance(self, file):
        authors = file.header.file_name.params[3]
        for author in authors:
            self.graph.add((self.graph.identifier, 
                            PROV.wasAttributedTo, 
                            Literal(author, datatype=XSD.string), 
                            self.graph.identifier))
        


def parse(stream):
    parser = Parser()
    try:
        return parser.parse(stream.read().decode("utf-8"))
    except:
        raise MalformedInputError("Unable to parse input.")


def ast_to_client(ast, graph):
    client = IFCLDClient(graph)
    FileVisitor().visit(client, ast)
    return client

from rdflib import ConjunctiveGraph, Graph
from rdflib.parser import Parser as RDFLibParser, InputSource
from rdflib.plugin import register


class STEPParser(RDFLibParser):
    def parse(self, source : InputSource, sink : Graph, **kwargs):
         # NOTE: A ConjunctiveGraph parses into a Graph sink, so no sink will be
        # context_aware. Keeping this check in case RDFLib is changed, or
        # someone passes something context_aware to this parser directly.
        if not sink.context_aware:
            conj_sink = ConjunctiveGraph(store=sink.store, identifier=sink.identifier)
        else:
            conj_sink = sink
        ast = parse(source.getByteStream())
        ast_to_client(ast, conj_sink)
        


register(
    "step",
    RDFLibParser,
    "stp2ifcld",
    "STEPParser",
)


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(
        description='Convert a STEP Part 21 file to IFC-LD')
    parser.add_argument('-f', '--file', dest='file', help='STEP Part 21 input file', required=True, default =sys.stdin)
    parser.add_argument('-s', '--serialization', dest='serialization', required=False, default = "turtle")
    args = parser.parse_args()
    g = ConjunctiveGraph(identifier = "http://ifc-ld.org/graphs#")
    g.parse(args.file, format="step")
    print(g.serialize(format=args.serialization))


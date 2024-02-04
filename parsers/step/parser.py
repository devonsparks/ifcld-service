# Standard Library
from pathlib import Path
from urllib.parse import quote as urlquote

# External Depedencies
from rdflib.graph import Collection
from rdflib.parser import Parser, InputSource
from dateutil import parser as dtparser
from rdflib import (ConjunctiveGraph, 
                    Graph, 
                    URIRef, 
                    BNode, 
                    Literal, 
                    Namespace, 
                    RDF, 
                    RDFS, 
                    XSD, 
                    PROV, 
                    DCTERMS
                    )


# Internal Dependencies
from .utils import Client, get_offset_map, get_ordered_attribute_set
from .visitors import FileVisitor
from .errors import MalformedInputError, ImpossibleConditionError
from .SCL.Part21 import Parser as SCLParser, TypedParameter

IFCLD_ID = Namespace("http://ifc-ld.org/ids#")

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

    client.graph.add((head, 
                      RDF.value, 
                      make_terminal(client, param), 
                      client.graph.identifier))
    
    if is_typed_parameter(param):
        client.graph.add((head, 
                          RDF.type, 
                          URIRef(param.type_name.lower()), 
                          client.graph.identifier))
    return head


def make_object(client, param):
    if is_ref(param):
        return URIRef(param, base=client.base_uri)
    elif is_terminal(param):
        return make_structured_value(client, param)
    elif is_collection(param):
            return make_list(client, param)
    elif is_typed_parameter(param):
        if len(param.params) > 1 or \
            (len(param.params) == 1 and is_collection(param.params[0])):
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
        self.base_uri = self.graph.identifier

        self._add_time_provenance(file)
        self._add_authorship_provenance(file)
        self._add_schema_metadata(file)
        self._apply_std_context(file)

    def begin_entity(self, entity, offset):
        self.current_entity = entity
        self.current_entity_type_uri = str(URIRef("#"+entity.type_name.lower(), base=self.vocab_uri))
        self.graph.add((URIRef(entity.ref, base=self.base_uri), 
                        RDF.type, 
                        URIRef(self.current_entity_type_uri), 
                        self.graph.identifier))

    def end_entity(self, entity, offset):
        self.current_entity = None
        self.current_entity_type_uri = None
    
    def begin_parameter(self, param, offset):
        if is_null(param) or is_derivable(param):
            return
        
        if self.current_entity_type_uri not in self.offset_map:
            raise Exception("Entity type {uri} not found in offset map".format(uri=self.current_entity_type_uri))
        
        property_uri = self.offset_map[self.current_entity_type_uri][offset]
        property = URIRef(property_uri)
        
        if is_collection(param) and str(property) not in self.ordered_attribute_set: # sets
            for item in param:
                self.graph.add((URIRef(self.current_entity.ref, base=self.base_uri), 
                        property, make_object(self, item), self.graph.identifier))
        else:
            self.graph.add((URIRef(self.current_entity.ref, base=self.base_uri),     # lists and everything else
                        property, make_object(self, param), self.graph.identifier))

        if property_uri.endswith("globalid"):
            """
            To every IFC instance with a GlobalID attribute, we ascribe
            a DCTERMS.subject, whose value is a URI built from the GlobalId string.
            This lets consumers collate properties of persistent objects by querying against
            this URI. 
            """
            self.graph.add((URIRef(self.current_entity.ref, base=self.base_uri),
                        DCTERMS.subject, 
                        URIRef(IFCLD_ID + param),
                        self.graph.identifier))


    def _add_time_provenance(self, file):
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

    def _add_schema_metadata(self, file):
        schema_name = file.header.file_schema.params[0][0].lower()
        self.vocab_uri = "http://ifc-ld.org/schemas/{ifc_schema}".format(ifc_schema=schema_name)
        self.offset_map = get_offset_map(schema_name)
        self.ordered_attribute_set = get_ordered_attribute_set(schema_name)
        self.graph.add((self.graph.identifier, 
                            DCTERMS.conformsTo, 
                            URIRef(self.vocab_uri+"#"),
                            self.graph.identifier))

    def _apply_std_context(self, file):
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.bind("ifc", Namespace(self.vocab_uri+"#"))

class STEPParser(Parser):
    def parse(self, source : InputSource, sink : Graph, **kwargs):
        # NOTE: ConjunctiveGraphs parse() into a Graph sink, 
        # so have to patch that before continuing.
        if not sink.context_aware:
            sink = ConjunctiveGraph(store=sink.store, identifier=sink.identifier)
        step_ast = self._step_parse(source)
        client = IFCLDClient(sink)
        FileVisitor().visit(client, step_ast)
        
    def _step_parse(self, source):
        parser = SCLParser()
        try:
            stream = source.getByteStream()
            return parser.parse(stream.read().decode("utf-8"))
        except:
            raise MalformedInputError("Unable to parse input.")



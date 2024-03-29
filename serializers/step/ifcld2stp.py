# SPDX-FileCopyrightText: © 2023-2024 Devon D. Sparks 
# SPDX-License-Identifier: AGPL-3.0

from rdflib import Graph
from parsers.step.utils import get_offset_map

"""
TODO: This module is incomplete. For now it's mostly sketches of queries. 
"""

def make_subject_map(graph):
    result = {}
    index = 0
    qres = graph.query("""
                SELECT DISTINCT ?subject 
                WHERE {
                       ?subject ?p ?o .
                FILTER(!isBlank(?subject)) . 
                       }
                """)
    for subject in qres:
        result[str(subject[0])] = index
        index = index + 1
    return result
import json

def make_subject_type_map(graph):
    result = {}
    qres = graph.query("""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
                       
                SELECT DISTINCT ?subject ?type
                WHERE {
                       ?subject rdf:type ?type . 
                       }
                """)
    for (subject, type) in qres:
        type_name = str(type).split("#")[-1].upper()
        result[str(subject)] = type_name
    return result 

def make_subject_value_map(graph):
    result = {}
    qres = graph.query("""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

                SELECT DISTINCT ?subject ?property ?value
                WHERE {
                       ?subject ?property ?value_node .
                FILTER(!isBlank(?subject)) . 
                ?value_node rdf:value ?value . 
                       }
                """)
    for (subject, property, value) in qres:
        result.setdefault(str(subject), {})
        result[str(subject)][str(property)] = value
    return result 
  
def make_offset_map(graph, schema_name):
    result = {}
    map = get_offset_map(schema_name)
    for entity_uri in map:
        result.setdefault(entity_uri, {})
        for i in range(len(map[entity_uri])):
            result[entity_uri][map[entity_uri][i]] = i
    return result

class File:
    def __init__(self):
        self.instances = []

class Instance:
    def __init__(self, id, type):
        self.id = id
        self.type = type
        self.attributes = []
            
class Attribute:
    def __init__(self, offset, value):
        self.offset = offset
        self.value = value

def serialize(graph):
    file = File()
    subject_map = make_subject_map(graph)
    offset_map = make_offset_map(graph, "ifc4")
    subject_type_map = make_subject_type_map(graph)
    for subject in subject_map:
        if subject not in subject_type_map: 
            continue
        print("#{id}= {ifc_type}({properties})".format(id=subject_map[subject], 
                                                       ifc_type=subject_type_map[subject],
                                                       properties=''))

print(json.dumps(make_subject_value_map(g), indent=4))
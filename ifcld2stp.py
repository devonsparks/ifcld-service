from rdflib import Graph

g = Graph().parse("out.ttl")

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

print(json.dumps(make_subject_map(g), indent=4))
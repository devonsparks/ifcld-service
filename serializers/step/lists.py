# SPDX-FileCopyrightText: © 2023-2024 Devon D. Sparks 
# SPDX-License-Identifier: AGPL-3.0

from rdflib import Graph

g = Graph().parse("lists.ttl")

def list_items_query(subject):
    return  """
    PREFIX list: <http://lists.com/schema#> 
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?item
    WHERE {
        <%s> list:values/rdf:rest*/rdf:first  ?item .
    }
    """%(subject)

def list_items_query2(subject):
    return  """
    PREFIX list: <http://lists.com/schema#> 
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?item
    WHERE {
        <%s> list:values/rdf:rest*/rdf:first  ?sublist .
        ?sublist rdf:rest*/rdf:first/rdf:value ?item .
    }
    """%(subject)

def list_position(subject):
    return """
    PREFIX list: <http://lists.com/schema#> 
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?element (COUNT(?mid)-1 as ?position) WHERE { 
    <%s> list:values/rdf:rest* ?mid . ?mid rdf:rest* ?node .
    ?node rdf:first ?element .
    }
    GROUP BY ?node ?element
    """%(subject)

def list_position2(subject):
    return """
    PREFIX list: <http://lists.com/schema#> 
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?item (COUNT(?mid)-1 as ?position) ?position2 WHERE { 
    <%s> list:values/rdf:rest* ?mid . ?mid rdf:rest* ?node .
    ?node rdf:first ?subelement .

    {
        SELECT ?item (COUNT(?mid2)-1 as ?position2) WHERE { 
        ?subelement rdf:rest* ?mid2 . ?mid2 rdf:rest* ?node2 .
        ?node2 rdf:first/rdf:value ?item .
    }
    GROUP BY ?node2 ?item
    }
    
    }
    GROUP BY ?node ?element
    """%(subject)

print(list_position("http://lists.com/list1d"))
for item in g.query(list_position2("http://lists.com/list2d")):
    print(item)


from rdflib import Graph

g = Graph()

g.parse("duplex.ttl")

site_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?site rdf:type bot:Site . 
} WHERE {
    ?site rdf:type ifc:ifcsite . 
}
"""

building_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?building rdf:type bot:Building . 
} WHERE {
    ?building rdf:type ifc:ifcbuilding . 
}
"""

storey_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?storey rdf:type bot:Storey . 
} WHERE {
    ?storey rdf:type ifc:ifcbuildingstorey . 
}
"""

has_building_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?site bot:hasBuilding ?building .  
} WHERE {
    ?site rdf:type ifc:ifcsite . 
    ?relaggregates rdf:type ifc:ifcrelaggregates . 
    ?relaggregates ifc:relatingobject ?site . 
    ?relaggregates ifc:relatedobjects ?building . 
}
"""

has_storey_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?building bot:hasStorey ?storey .  
} WHERE {
    ?building rdf:type ifc:ifcbuilding . 
    ?relaggregates rdf:type ifc:ifcrelaggregates . 
    ?relaggregates ifc:relatingobject ?building . 
    ?relaggregates ifc:relatedobjects ?storey . 
    ?storey rdf:type ifc:ifcbuildingstorey . 
}
"""

has_space_q = """
prefix bot: <https://w3id.org/bot#> 
prefix ifc: <http://ifc-ld.org/schemas/ifc2x3#> 
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 

CONSTRUCT {
    ?storey bot:hasSpace ?space .  
} WHERE {
    ?storey rdf:type ifc:ifcbuildingstorey . 
    ?relaggregates rdf:type ifc:ifcrelaggregates . 
    ?relaggregates ifc:relatingobject ?storey . 
    ?relaggregates ifc:relatedobjects ?space . 
    ?space rdf:type ifc:ifcspace . 
}
"""



g2 = Graph()
for triple in g.query(has_space_q):
    g2 = Graph()
    g2.add(triple)

print(g2.serialize())
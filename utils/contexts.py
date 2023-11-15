
BaseCtx = {
    # "id": "@id",
    # "type": "@type",
    # "key": "@index",
    # "value": "@value",
    "meta": "@nest",
    "who": {"@id": "http://ifc-ld.org#who", "@nest": "meta"},
    "when": {"@id": "http://ifc-ld.org#when", "@nest": "meta"},
    "objectof": {
        "@type": "@id",
        "@id": "http://ifc-ld.org#objectof", "@nest": "meta"
    },

    "slotof": {
        "@type": "@id",
        "@id": "http://ifc-ld.org#slotof", "@nest": "meta"
    },

    "contents": {"@id":"http://ifc-ld.org#contents", "@container":"@list"},
    "values":{"@id":"http:/ifc-ld.org#values", "@container":"@list"},
    "@vocab": "http://ifc-ld.org/",
    "@base": "http://ifc-ld.org/",
    "xsd":"http://www.w3.org/2001/XMLSchema#",
    "ifc2x3": "http://buildingsmart.org/standards/ifc2x3/",
    "ifc4": "http://buildingsmart.org/standards/ifc4/"
}

ReverseFramedContext = {
    **BaseCtx,
    **{"objects": {"@reverse": "objectof"}, 
       "slots": {"@reverse": "slotof"}}
}


IndexBasedContext = {
    **BaseCtx,
    **{"objects": {"@id": "http://ifc-ld.org#object", "@container": "@index"}},
    **{"slots": {"@id": "http://ifc-ld.org#slot", "@container": "@index"}}
}

SetBasedContext = {
    **BaseCtx,
    **{"objects": {"@id": "http://ifc-ld.org#object", "@container": "@set"}},
    **{"slots": {"@id": "http://ifc-ld.org#slot", "@container": "@set"}}
}

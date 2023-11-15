from pyld import jsonld


# Override PyLD's default Requests-based document loader 
# to support loading @contexts inline. 
jsonld.set_document_loader(lambda doc, _: {"contentType": "application/json",
                                           "document": doc,
                                           "contextUrl": None,
                                           "documentUrl": None})

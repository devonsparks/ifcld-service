
import uuid


from flask import Flask, request, abort, Response
from rdflib import ConjunctiveGraph, Graph
from rdflib.plugin import plugins
from rdflib.parser import Parser
from rdflib.serializer import Serializer
from mimeparse import best_match, parse_mime_type

import parsers
from profiles import enrich_graph, get_supported_profiles

app = Flask(__name__)


def supported_mimetypes(rdflib_type):
    """
    For a given RDF plugin type (e.g., Parser, Serializer), 
    return a list of all plugin names of that type whose name
    is also a valid mime type. 
    """
    for plugin in plugins(None, rdflib_type):
        try:
            (type, subtype, _) = parse_mime_type(plugin.name)
            yield "{type}/{subtype}".format(type=type, subtype=subtype)
        except:
            continue

def get_ifc_version_uri(graph):
    from rdflib import DCTERMS
    for value in graph.objects(predicate=DCTERMS.conformsTo):
        if str(value).startswith("http://ifc-ld.org/schemas/"):
            return value

def get_content_location(request):
    """
    Retrieve preferred base URI from HTTP request header or generate one otherwise. 
    """
    return request.headers.get('content-location') or \
        "http://ifc-ld.org/graphs/{guid}".format(guid=uuid.uuid4())


"""
Cache all available input and output mimetypes from rdflib
"""
input_mimetypes = list(supported_mimetypes(Parser))
output_mimetypes = list(supported_mimetypes(Serializer))


@app.route("/instances", methods=["POST"])
def graphs():
    input_format = best_match(input_mimetypes, request.headers['content-type'])
    output_format = best_match(output_mimetypes, request.headers['accept'])

    if not input_format:
        return abort(415)                   # Unsupported Media Type
    
    if not output_format:
        return abort(406)                   # Not Acceptable
    
    if not request.data:
        return Response("No Content", 204)  # No Content

    g = ConjunctiveGraph(identifier = get_content_location(request))

    try: 
        g.parse(data=request.data, format=input_format)
        ifc_version = get_ifc_version_uri(g)
    except:
        return abort(422)                    # Unprocessable Entity 
    
    content_profiles = set([ifc_version])
    if request.headers.get('accept-profile'):
        acceptable_profiles = request.headers['accept-profile'].split(",")
        content_profiles = content_profiles.union(enrich_graph(g, acceptable_profiles, ifc_version))

    try:
        content = g.serialize(format=output_format)
        resp =  Response(content, mimetype=output_format)
        resp.headers['Content-Profile'] = ','.join(content_profiles)
        resp.headers['Vary'] = ",".join(set(request.headers.keys(lower=True))\
                .intersection(set(["accept", "accept-profile", "content-location"])))
        return resp
    except: 
        return abort(Response("Serialization failure. This is likely a bug.", 500))


if __name__ == '__main__':
    #from werkzeug.middleware.profiler import ProfilerMiddleware
    #app.wsgi_app = ProfilerMiddleware(app.wsgi_app)
    app.run(debug=False, host='0.0.0.0')
    app.logger.info("Supported input formats: {}".format(input_mimetypes))
    app.logger.info("Supported output formats: {}".format(output_mimetypes))
# IFC-LD Instance Builder

This repository holds a reference implementation of the [IFC-LD](http://ifc-ld.org) instance builder. The instance builder exposes an HTTP interface for converting and enriching IFC/STEP to the IFC-LD data model, its various serializations, and all enrichment profiles that have been defined. It is **pre-alpha** software, provided as-is while development continues. Pull requests are welcome.

The IFC-LD instance builder HTTP interface leans heavily on the HTTP standard, supporting both [Content Negotiation](https://www.rfc-editor.org/rfc/rfc9110.html#name-proactive-negotiation) and [Content Negotation by Profile](https://profilenegotiation.github.io/I-D-Accept--Schema/I-D-accept-schema).

# Usage

Given a Python3 installation, the service can either be run locally:

```
$ python3 -m venv env
$ source env/bin/activate
$ pip3 install -r requirements.txt
$ python3 service.py
```

which will expose the service on port 5000 (currently in debug mode - remember, pre-alpha :), or via the included Dockerfile.

```
docker build --tag=ifcld-instance-builder .
docker run -d -p 5000:5000 ifcld-instance-builder
```

Once launched, IFC-STP files can be converted by issuing a `POST` to the `/instances` endpoint:

```
curl --location --request POST 'localhost:5000/instances' \
--header 'Content-Type: model/step' \
--header 'Accept: text/turtle' \
--header 'Content-Location: http://myserver.com#' \
--data-raw 'ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('\''ViewDefinition [CoordinationView]'\''),'\''2;1'\'');
FILE_NAME('\''0001'\'','\''2011-09-07T12:28:29'\'',('\'''\''),('\'''\''),'\''Autodesk Revit Architecture 2011 - 1.0'\'','\''20100326_1700 (Solibri IFC Optimizer)'\'','\'''\'');
FILE_SCHEMA(('\''IFC2X3'\''));
ENDSEC;
DATA;
#58 = IFCPROPERTYSINGLEVALUE('\''ThermalTransmittance'\'', $, IFCREAL(2.400E-1), $);
ENDSEC;
END-ISO-10303-21;'
```

Headers used to control responses include:

 - `Accept`: To set the mime type of the response. `text/turtle`, `application/rdf+xml`, `application/json` are supported. `text/turtle` is default.

- `Content-Location`: Overrides the `@base` URI for all subjects in the graph. `http://ifc-ld.org/graphs/{runtime-guid}#` is default.

- `Accept-Profile`: Triggers enrichment of the response graph with external Profiles. `https://w3id.org/bot#` is supported. No default.

Currently supported IFC versions:
- IFC2x3
- IFC4
- IFC4x1
- IFC4x2

# Notes

Current response time is poor. Calls are synchronous. Profiling shows bottlenecks deep in the RDFLib runtime. Consider changing the RDFLib store backend, or otherwise switching to a higher performance RDF processing engine (Redland?).

# License

AGPLv3. See [LICENSE.md](LICENSE.md).

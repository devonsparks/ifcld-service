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
docker build --tags=ifcld-instance-builder .
docker run -d -p 5000:5000 ifcld-instance-builder
```

# Notes

Current response time is poor. Profiling shows bottlenecks deep in the RDFLib runtime. Consider changing the RDFLib store backend, or otherwise switching to a higher performance RDF processing engine (Redland?).

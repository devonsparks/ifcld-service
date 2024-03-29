# SPDX-FileCopyrightText: © 2023-2024 Devon D. Sparks 
# SPDX-License-Identifier: AGPL-3.0

from urllib import request
import json

from pyshacl import Validator
from rdflib import Graph, Namespace

def add_profile(graph, rule_graph):
    v = Validator(graph, shacl_graph=rule_graph, 
                  options={"advanced": True, "inplace": True})
    v.run()
    

def get_supported_profiles():
    with request.urlopen("http://ifc-ld.org/profiles/index.json") as response:
        return json.loads(response.read())


def get_profile_graph(profile_location_uri, ifc_version_uri):
    with request.urlopen(profile_location_uri) as response:
        data = response.read()
        # we need to append specific ifc version prefix (the alternative to one module per ifc version)
        data = "@prefix ifc: <{}> .\n".format(ifc_version_uri).encode() + data
        return Graph().parse(data=data)
    

def enrich_graph(graph, accept_profiles, ifc_version):
    added_profiles = set([])
    for profile_uri in accept_profiles:
        supported_profiles = get_supported_profiles()
        if profile_uri in supported_profiles:
            try: 
                profile_details = supported_profiles[profile_uri]
                profile_graph = get_profile_graph(profile_details["url"], ifc_version)
                add_profile(graph, profile_graph)
                graph.bind(profile_details["prefix"], profile_uri)
                added_profiles.add(profile_uri)
            except:
                continue
    return added_profiles
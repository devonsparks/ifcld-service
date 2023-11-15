# Standard Library
from pathlib import Path
from urllib.parse import quote as urlquote
from json import dumps, loads

# External Depedencies
from SCL.Part21 import Parser, TypedParameter
from dateutil import parser as dtparser

# Internal Dependencies
from utils.common import doc
from utils.parsing.client import IClient
from utils.parsing.visitors import FileVisitor
import utils.guid as guid

Type = "type"
Val = "val"
Added = "add"
To = "to"
From = "from"
Ref = "ref"
On = "on"
Graph = "changeset"

class Stack:
    def __init__(self,  *items):
        self.items = list(items)

    def push(self, *items):
        for item in items:
            self.items.append(item)

    def pop(self):
        return self.items.pop()

    def peek(self, offset=-1):
        return self.items[-1]

    def clone(self):
        return self.__class__(*self.items)

    def size(self):
        return len(self.items)


class URIStack(Stack):
    def push(self, *items):
        super().push(*(urlquote(i) for i in items))

    def toURI(self, limit = None):
        return "/".join(self.items[:limit])




def property_offset_map(schema, path="static/names/"):
        propsfile = Path("%s/%s.json"%(path, schema))
        if propsfile.is_file():
            with propsfile.open('r') as f:
                return loads(f.read())["names"]


class JSONClient(IClient):
    def __init__(self, idbase="http://ifc-ld.org", typebase="http://buildingsmart.org/standards", **options):
        self.doc =  doc()
        self.idstk = URIStack(idbase)
        self.typestk = URIStack(typebase)
        self.options = options
        self.idbase = idbase
        self.typebase = typebase

    def here(self):
        return self.idstk.toURI()

    def beginFile(self, file, offset):
        self.typestk.push(file.header.file_schema.params[0][0].lower())
        self.idstk.push(guid.new())
        self.map = property_offset_map(self.typestk.peek()) or {}
        self.doc["@id"] = "#"
        self.doc["@graph"] = []
        self.idstk.pop()

    def beginEntity(self, entity, offset):
        
        self.idstk.push(entity.ref[1:])
        self.typestk.push(entity.type_name.lower())
        self.doc["@graph"].append({"@id":entity.ref[1:], "@type":entity.type_name.lower()})
        

    def beginParameter(self, param, offset):
        # Fetch the index _before_ we go modifying the type stack.
        self.doc["@graph"][-1][offset] = {"rdf:value":param}


    def endFile(self, file, offset):
        return 
        assert self.idstk.size() == 1   # idbase remains
        assert self.typestk.size() == 2 # typebase and schema version remain

    def endEntity(self, entity, offset):
        self.idstk.pop()  # entity ID
        self.typestk.pop()

    def endParameter(self, param, offset):
        pass

    def toJSON(self):
        return dumps(self.doc, indent=4, sort_keys=True)

    def dispatch(self, param, offset):
        cls = self.map.get(self.typestk.peek())[offset] or str(offset)

        if is_ref(param):
            stk = URIStack(self.idbase)
            stk.push(param[1:])

            if self.doc[On].get(stk.toURI()):
                self.doc[On][stk.toURI()][Added].append({Type:cls, From:{Ref:self.idstk.toURI()}})
            else:
                self.doc[On][stk.toURI()] = {Added:[{Type:cls, From:{Ref:self.idstk.toURI()}}]}

            return {To:{Ref:stk.toURI()}, Type:cls}

        elif is_null(param) or is_derivable(param):
            return None

        elif is_enum(param) or is_string(param) or is_float(param) or is_int(param):
            return {To:{Val:param}, Type:cls}

        elif isinstance(param, TypedParameter):
            stk = self.typestk.clone()
            stk.pop() # current param
            stk.pop() # current entity
            stk.push(param.type_name)
            return {To:{Val:param.params}, Type:stk.toURI()}
        elif isinstance(param, list):
            return {"list":[self.dispatch(p, offset) for p in param], Type:cls}
        else:
            raise Exception("Unexpected type", param)


def is_enum(param):
    return isinstance(param, str) and param.startswith('.') and param.endswith('.')


def is_ref(param):
    return isinstance(param, str) and param.startswith('#') and param[1:].isdigit()


def is_terminal(param):
    return not is_ref(param)


def is_null(param):
    return param == "$"

def is_derivable(param):
    return param == "*"

def is_collection(param):
    return isinstance(param, list)

def is_string(param):
    return isinstance(param, str)

def is_number(param):
    return isinstance(param, int) or isinstance(param, float)

def is_float(param):
    return isinstance(param, float)

def is_int(param):
    return isinstance(param, int)

def is_ifcguid(param):
    return isinstance(param, str) and len(param) == 22 and all(ch in guid.chars for ch in param)

class MalformedInputError(ValueError):
    pass


def parse(stream):
    parser = Parser()
    try:
        return parser.parse(stream.read())
    except:
        raise MalformedInputError("Unable to parse input.")


def stp2new(stream):
    # generate the P21 abstract syntax tree
    ast = parse(stream)

    client = JSONClient()
    FileVisitor().visit(client,  ast)

    return client.doc 
    

ctx =  {
        "@vocab":"http://vocab.com/", "@base":"http://server.com/", 
        "changeset":"@id", 
        On:{"@container":"@id"}, 
        "ref":"@id",
        "val":"@value",
        "type":"@type"}
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Convert a STEP Part 21 file to JSON-LD')
    parser.add_argument('-f', '--file', dest='file', 
                        default=0, help='STEP Part 21 input file')

    parser.set_defaults(stdpkg=True)

    args = parser.parse_args()
    with open(args.file) as stream:
        pkg = stp2new(stream)
        pkg["@context"] = ctx
        print(dumps(pkg, indent=4))

import json
from textwrap import dedent
from urllib.parse import unquote
import utils.common as common


class Element(object):
    def serialize(self, data):
        return None


class Package(Element):
    def serialize(self, data):
        e = Entity()
        children = [e.serialize(el) for el in data["contents"]]
        template = dedent('''\
        ISO-10303-21;
        HEADER;
        FILE_DESCRIPTION(('unknown'),'2;1');
        FILE_NAME(
        /* name */ '{name}',
        /* time_stamp */ '{timestamp}');

        FILE_SCHEMA (('{schema}'));
        ENDSEC;

        DATA;
        {children}
        ENDSEC;

        END-ISO-10303-21;
        ''')
        return template.format(name=self.get_name(data), 
                   timestamp=self.get_timestamp(data), 
                   schema=self.get_schema(data), 
                   children='\n'.join(children))
    def get_timestamp(self, data):
        return unquote(data["id"].split("/")[-2]).split(common.Separator)[1]
    def get_name(self, data):
        return unquote(data["id"].split("/")[-2]).split(common.Separator)[0]
    def get_schema(self, data):
        return data["class"].split("/")[-2]

class Entity(Element):
    def serialize(self, data):
        if not isinstance(data["contents"], list):
            data["contents"] = [data["contents"]]
        children = [self.dispatch(el).serialize(el) for el in data["contents"]]
        localid = data["id"].split("/")[-2]
        klass = data["class"].split("/")[-2]
        template="#{localid}= {klass}({parameters});"
        return template.format(localid=localid, klass=klass, parameters=','.join(children))

    def dispatch(self, el):
        return 
        targetTypeMap = {"id": Ref, "Number":Number, "String":String, 
        "Collection":Collection, "Derivable":Derivable, "Null":Null, "Enum":Enum}
        return targetTypeMap[el["target"]["targetType"]]()

class Slot(Element):
    def serialize(self, data):
        return "{value}".format(value=data["contents"]["@value"])

class Datum(Element):
    def serialize(self, data):
        if data["contents"].get("@value"):
            return "{value}".format(value=data["contents"]["@value"])
        else:
            return "$"

def json2stp(f):
    data = json.loads(f.read())
    p = Package()
    return p.serialize(data)


if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description='Convert a JSON-LD file to its STEP Part 21 counterpart')
    parser.add_argument('-f', '--file', dest='file', type=argparse.FileType('r'), default=sys.stdin, help='JSON-LD input file')
    args = parser.parse_args()
    with open(args.file) as f:
        print(json2stp(f))

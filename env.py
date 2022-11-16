

from uuid import uuid4
import json
from collections import defaultdict

def warn(msg):
	print("Warning:%s"%msg)

class MemScene:
	def __init__(self, *constructors):
		self.constructors = constructors
		assert len(self.constructors) > 0
		self.db = {}

	def add_constructors(self, *constructors):
		self.constructors = list(constructors) + self.constructors
	
	def env_for(self, bindings):
		for constructor in self.constructors:
			if constructor.can_parse(bindings):
				return constructor(self, bindings)
	
	def new_id(self):
		return str(uuid4())
	
	def has_id(self, id):
		return bool(self.db.get(id))

	def create(self):
		"POST /envs"
		id = self.new_id() 
		self.db[id] = {"id":id}
		return self.db[id].get("id")

	def get(self, id):
		"GET /envs/<id>/"
		return self.db.get(id)
	
	def put(self, bindings):
		"PUT /<env>/<id>/"
		if not bindings.get("id"):
			bindings["id"] = self.new_id()
		kvs = {}
		for (k, v) in bindings.items():
			kvs[k] = self.put(v) if isinstance(v, dict) else v
		self.db[bindings.get("id")] = kvs
		return bindings.get("id")


class SEnv:
	ParentSymbol = "*"
	def __init__(self, space, bindings = {}):
		self.space = space
		self.bindings = self.space.get(self.space.put(bindings))
		assert self.bindings["id"]
	
	def to_json(self):
		return self.bindings

	@classmethod
	def can_parse(self, bindings):
		"""
		Answers whether this class can parse a given set of bindings. Used primarily
		Used for finding the appropriate class constructor for a set of bindings.
		"""
		return True

	def get(self, var):
		"Find the innermost Env where var appears."
		if var in self.bindings:
			value = self.bindings[var]
			if isinstance(value, list):
				return [self.space.env_for(self.space.get(id)) for id in value]
			elif self.space.has_id(value) and not var == "id":
				return self.space.env_for(self.space.get(value))
			else:
				return value
		elif self.bindings.get(SEnv.ParentSymbol):
			return self.space.env_for(self.space.get(self.bindings.get(SEnv.ParentSymbol))).get(var)
		else: 
			raise ValueError("%s is not defined"%(var,))
	
	def get_all(self, var):
		"Find all Envs where var appears, starting at the innermost"
		try:
			yield self.get(var)
			yield from self.get(SEnv.ParentSymbol).get_all(var)
		except ValueError:
			return
		
	def _resolve(self, var, result, include_ids = True):
		"The helper method of resolve(), handling recursive calls."
		here = self.get(var)
		if not isinstance(here, SEnv):
			return here
		else:
			for k in here.bindings.keys():
				if k == "id" and not include_ids:
					continue
				result[k] = here._resolve(k, result[k], include_ids)
		return dict(result)

	def resolve(self, var, include_ids = True) -> dict:
		"Resolves a variable by returning it, along with all of its links." 
		inftdict = lambda: defaultdict(inftdict)
		return self._resolve(var, inftdict(), include_ids)
	
	def update(self, bindings):
		self.bindings = self.space.get(self.space.put({**self.bindings, **bindings}))
		return self

	def delete(self, var):
		del self.bindings[var]
		return self.update(self.bindings)

	def create(self, bindings = {}):
		"Creates a new sub-Env with a given set of bindings"
		bindings[SEnv.ParentSymbol] = self.bindings["id"]
		return self.space.env_for(bindings)
	
	def declare(self, key, shortcut = None, type = None):
		if not shortcut: 
			shortcut = key
			type = "@vocab"
		if not type:
			type = "@id"
		self.get("@context").update({key:{"@id":shortcut, "@type":type}})

	def set(self, key, value):
		"Set a specific key, value pair. The semantics of the key, value pair should be declared with declare()."
		if not key in self.get("@context").bindings:
			warn("key \"%s\" has not been declared. Use %s.declare() to define this first."%(key, self.__class__.__name__))
		return self.update({key:value})
		
	def link_on(self, env, key):
		#key = env.get(key)
		assert isinstance(key, str)
		if self.space.has_id(self.bindings.get(key)): 	# already binds singleton id? 
				return self.set(key, [env.get("id")] + [self.bindings[key]])
		elif isinstance(self.bindings.get(key), list):	# already binds list of ids?
			return self.set(key, [env.get("id")] + self.bindings[key])
		else:
			return self.set(key, env.get("id"))
		
	def link(self, target, rel = None):
		rel = rel or target
		self.link_on(target, rel.get(rel.get("source_key")))
		target.link_on(self, rel.get(rel.get("target_key")))
		return self


	def __repr__(self):
		return "%s(%s)"%(self.__class__.__name__, json.dumps(self.to_json(), indent=4))


S = MemScene(SEnv)

Root = SEnv(S, {"id":"Root","@context":{"@vocab":"http://ifc-ld.org#"}})
Root.declare("description", type="xsd:string")
Root.declare("name")
Component = Root.create({"id":"Component", "name":"Root", "description":"A Component", "entities":[]})
Relation = Component.create({"target":""})

e1 = Component.create()
e1.declare("name", "http://foo.com#name", "xsd:string")
e1.attr("name", "e1")
e1.attr("description", "foobar")


#e1.link(e2, Relation)


"""

decomp1 = Decomposes.create()
decomp2 = Decomposes.create()
e1 = Entity.create({"name":"e1"})
c1 = Component.create({"name":"c1"})
c2 = Component.create({ "name":"c2", "foo":"bar"})


# A one-way Entity-Component link
e1.link(c1, "name")

# A two-way, Entity-Component link
e1.bilink(c2, "name")


e1.trilink(e2, decomp1)

e1.trilink(Entity.create({"name":"e3"}), decomp2)
#e1.next(e2)
"""


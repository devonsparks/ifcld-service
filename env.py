

from uuid import uuid4
from xml.dom.pulldom import parseString
from json_logic import jsonLogic as logic
import json
import graphviz

def match(**kwargs):
	return {"and": [{"==": [{"var": k}, v]} for (k, v) in kwargs.items()]}

def stream(slot):
	if not slot: return
	yield slot
	yield from stream(slot.prev)

def atom(value):
	return isinstance(value, float) or isinstance(value, int) or isinstance(value, str)


from collections import defaultdict

def kvs(bindings = {}):
    return defaultdict(lambda: kvs(), bindings)

class MemSpace:
	def __init__(self):
		self.db = {}
	
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

	def get(self, var):
		"Find the innermost Env where var appears."
		if var in self.bindings:
			value = self.bindings[var]
			if self.space.has_id(value) and not var == "id":
				return SEnv(self.space, self.space.get(value))
			else:
				return value
		elif self.bindings.get(SEnv.ParentSymbol):
			return SEnv(self.space, self.space.get(self.bindings.get(SEnv.ParentSymbol))).get(var)
		else: return None #raise ValueError("%s is not defined"%(var,))
	
	def update(self, bindings):
		self.bindings = self.space.get(self.space.put({**bindings, **self.bindings}))
		return self

	def delete(self, var):
		del self.bindings[var]
		return self.update(self.bindings)

	def create(self, bindings = {}):
		"Creates a new sub-Env with a given set of bindings"
		bindings[SEnv.ParentSymbol] = self.bindings["id"]
		return SEnv(self.space, bindings)
	
	def halflink(self, env, key):
		key = env.get(key) or env.get("id")
		assert isinstance(key, str)
		return self.update(dict(zip([key], [env.get("id")])))
		
	def link(self, env, key = "name"):
		self.halflink(env, key)
		env.halflink(self, key)
		return self

	def relate(self, target, rel):
		"Relations link two environments via third using a standard description"
		self.link(rel, key = "relating")
		target.link(rel, key = "related")
		return self
	
	def next(self, env):
		self.update({"next":env.get("id")})

	def __repr__(self):
		return "%s(%s)"%(self.__class__.__name__, json.dumps(self.to_json(), indent=4))



S = MemSpace()

Root = SEnv(S, {"type":"Root", "id":"Root", "description":"I am an Env", "relating":"relating", "related":"related"})
Entity = Root.create({"type":"Entity", "id":"Entity"})
Component = Root.create({"type":"Component", "id":"Component"})
Decomposes = Component.create({"type":"Relation", "name":"decomposition", "relating":"rel:decomposition", "related":"rel:decomposition", "description":"I describe relations between"})

decomp1 = Decomposes.create({})
e1 = Entity.create({"name":"e1"})
c1 = Component.create({"name":"c1"})
c2 = Component.create({"attach":"foo", "name":"c2", "foo":"c2-gets-attached-here"})
e2 = Entity.create({"name":"e2"})

#e1.link(c1)

#e1.relate(e2, decomp1)

e1.next(e2)

#### Everything below this is scrap to pull from

class Slot:
	ids = {}
	def __init__(self, name = None, prev = None):
		self.id = str(uuid4())
		self.name = name
		self.prev = prev
		self.__class__.ids[self.id] = self
		self.contents = None

	@classmethod
	def get_by_id(cls, id):
		return cls.ids.get(id)

	def find(self, name):
		if not name: 
			here = self
			while here.prev:
				here = here.prev
			return here
		elif self.name == name:
			return self
		elif self.prev and isinstance(self.prev, Slot):
			return self.prev.find(name)
		else:
			raise ValueError("%s is not defined"%(name,))

	def spawn(self, name):		return self.__class__(name, self)
	def set(self, contents):
		self.contents = contents
		return self
	
	def copy(self):
		"""
		Create a complete copy of the Slot chain back to the root
		"""
		return self.__class__(self.name, self.prev.copy() if self.prev else None).set(self.contents)
	
	def extend(self, slot): 
		"""
		attaches the current Slot chain as the extension of a given slot. Can be used to make new branches.
		"""
		self.find(None).prev = slot
		return self

	def clone(self, target = None):
		"""
		Creates a copy of the current Slot chain and attaches it to this one. 
		"""
		return self.copy().extend(target or self)

	def to_json(self):
		if self.prev:
			yield from self.prev.to_json()
		yield {"name":self.name, "contents":self.contents}



class Container:
	ids = {}
	def __init__(self, name = None, contents = None, prev = None):
		self.id = str(uuid4())
		self.name = name
		self.prev = prev
		self.contents = contents 
		self.__class__.ids[self.id] = self
	
	@classmethod
	def get_by_id(cls, id):
		return cls.ids.get(id)

	def find(self, name):
		if self.name == name:
			return self
		elif self.prev and isinstance(self.prev, Container):
			return self.prev.find(name)
		else:
			raise ValueError("%s is not defined"%(name,))

	def spawn(self, name, contents = None):
		return self.__class__(name, self.contents, self)

	def copy(self, name, deep = True):
		if not deep:
			return self.spawn(name, self.contents if isinstance(self.contents, Container) else None)
		else:
			return self.spawn(name, self.contents.copy(self.contents.name) if isinstance(self.contents, Container) else None)

	def has(self, name):
		self.contents = self.contents.spawn(name)
		return self.contents 

	def set(self, contents):
		self.contents = contents
		return self

	def __repr__(self):
		return "%s(%s)"%(self.__class__.__name__, self.name)

	def draw(self):
		return self._draw(graphviz.Digraph(comment='Container Map', format='png', strict = True))

	def _draw(self, dot):
		dot.node(self.id, label = self.name)
		if self.prev:
			self.prev._draw(dot)
			dot.edge(self.id, self.prev.id, color="red", label="prev")
		if isinstance(self.contents, Container):
			self.contents._draw(dot)
			dot.edge(self.id, self.contents.id, color="blue", label="contents")
		return dot

	def to_json(self):
		return {"name":self.name, 
			"prev":self.prev.to_json() if isinstance(self.prev, Container) else None,  
			"contents":self.contents.to_json() if isinstance(self.contents, Container) else None}

class Env:
	"An environment: a dict of {'var':val} pairs, with an outer Env."
	ids = {}
	def __init__(self, bindings={}, outer=None):
		self.bindings = bindings
		self.outer = outer
		self.id = str(uuid4())
		self.name = bindings.get("name") or self.id
		self.__class__.ids[self.id] = self

	
	def __getitem__(self, var):
		return self.get(var)

	def get(self, var):
		"Find the innermost Env where var appears."
		if var in self.bindings:
			result = self.bindings[var]
			if Env.ids.get(result):
				return Env.ids[result]
			else:
				return result
		elif not self.outer is None:
			return self.outer.get(var)
		else: raise ValueError("%s is not defined"%(var,))

	def to_json(self):
		def recur(v):
			return v.to_json() if isinstance(v, Env) else v
		return {"bindings":{k:recur(v) for k, v in self.bindings.items()}}


	def update(self, bindings):
		self.bindings.update(bindings)
		return self

	def attach(self, env):
		binding = {}
		binding[env.bindings.get("name") or env.id] = env
		self.update(binding)
		return self

	def detach(self, name):
		del self.bindings[name]
		return self

	def create(self, bindings = {}):
		"Creates a new sub-Env with a given set of bindings"
		return self.__class__(bindings, self)

	def clone(self, deep = True):
		"Creates a full copy of the current environment as a sub-Env"
		bindings = self.bindings.copy()
		if deep:
			for (k, v) in bindings.items():
				bindings[k] = v.clone() if isinstance(v, Env) else v
		return self.create(bindings)
	
	
	def keys(self):
		return set(self.bindings.keys())


	def draw(self, dot):
		shape = ""
		for (k, v) in self.bindings.items():
			shape = shape + "{%s|<%s>%s}|"%(k,k, v if atom(v) else "*")
			if isinstance(v, Env):
				v.draw(dot)
				dot.edge("%s:%s:e"%(self.id, k), v.id, style="dashed")
		shape = "{%s}"%(shape[:-1])
		dot.node(self.id, shape)
		if self.outer:
			self.outer.draw(dot)
			dot.edge(self.id, self.outer.id)
"""
class Component(Env):
	def slot(self, name):
		return self.get(name)

class Entity(Env):
	def component(self, name):
		return self.get(name)


class Package(Env):
	def entity(self, name):
		return self.get(name)



def blank():
	return graphviz.Digraph(comment='Env Map', format='png', strict = True, node_attr={'shape': 'record'})



dot = blank()

C = Component({"name":"C", "description":None})
rel = C.clone(True).update({"name":"rel"})
loc = C.clone(True).update({"name":"loc"})



e1 = Entity({})
e1.attach(rel)
e1.attach(loc)

e1.component("loc").update({"lat":32, "lon":2.5})

p1 = Package()
p1.attach(e1)


rel.update({"relating":p1.id, "related":[e1.id]})
p1.draw(dot)
dot.render()


# consider higher order find(*logics) function, that takes a seri

before = blank()
e1.draw(before)
before.render('before.png')


e2 = e1.clone(True) # By default, copy both the entity and all the Components attached to it. 
e2.find("help").update({"title":"E2 title"})
after = blank()
e2.draw(after)

after.render('after.png')
"""
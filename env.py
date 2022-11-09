from re import I
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

	def spawn(self, name):
		return self.__class__(name, self)

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
		return self.find(var)

	def find(self, var):
		"Find the innermost Env where var appears."
		if var in self.bindings:
			result = self.bindings[var]
			if Env.ids.get(result):
				return Env.ids[result]
			else:
				return result
		elif not self.outer is None:
			return self.outer.find(var)
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

class Component(Env):
	def slot(self, name):
		return self.find(name)

class Entity(Env):
	def component(self, name):
		return self.find(name)


class Package(Env):
	def entity(self, name):
		return self.find(name)



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
"""

before = blank()
e1.draw(before)
before.render('before.png')


e2 = e1.clone(True) # By default, copy both the entity and all the Components attached to it. 
e2.find("help").update({"title":"E2 title"})
after = blank()
e2.draw(after)

after.render('after.png')
"""
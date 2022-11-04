
import uuid
import json
from typing import List
from json_logic import jsonLogic as logic
from abc import ABC, abstractmethod, abstractclassmethod
from itertools import chain


class Space(ABC):
    """
    As in, "address space". Spaces are an abstraction of an address layer, and not part of the serialization format.

    Note that an address space is different from a dedicated storage layer. A space is a mechanism to look something up.
    Individual results may come from different locations based on the ID. The dispatch strategy is left to the Space implementation.

    # All of these operations are intentionally idempotent.
    """
    # Because this isn't part of the serialization format, maybe a good place to enact notifications.
    
    def __init__(self, pkgcls, entitycls, compcls, litcls, refcls):
        self.Package = pkgcls
        self.Entity = entitycls
        self.Component = compcls
        self.Literal = litcls
        self.Ref = refcls
        self.constructors = [pkgcls, entitycls, compcls, litcls, refcls]

    @abstractmethod
    def _iter_packages(self):
        """
        Concrete subclasses should implement an iterator over all available Packages. 
        """

    @abstractmethod
    def _iter_entities(self):
        """
        Concrete subclasses should implement an interator over all available Entities.
        """
    
    @abstractmethod
    def _iter_components(self):
        """
        Concrete subclasses should implement an interator over all available Components.
        """

    @abstractmethod
    def put_package(self, json):
        """
        Concrete subclasses should implement a idempotent operation to commit
        a JSON description of a Package to storage.
        """

    @abstractmethod
    def put_entity(self, json):
        """
        Concrete subclasses should implement a idempotent operation to commit
        a JSON description of a Entity to storage.
        """

    @abstractmethod
    def put_component(self, json):
        """
        Concrete subclasses should implement a idempotent operation to commit
        a JSON description of a Component to storage.
        """

    def _query(self, jsonlogic, iterator):
        for asset in iterator:
            if logic(jsonlogic, asset):
                yield asset

    def query_packages(self, jsonlogic):
        for result in self._query(jsonlogic, self._iter_packages()):
            yield self.Package(self, **result)

    def query_entities(self, jsonlogic):
        for result in self._query(jsonlogic, self._iter_entities()):
            yield self.Entity(self, **result)

    def query_components(self, jsonlogic):
        for result in self._query(jsonlogic, self._iter_components()):
            yield self.Component(self, **result)

    def get_package(self, jsonlogic):
        return next(self.query_packages(jsonlogic))
    
    def get_entity(self, jsonlogic):
        return next(self.query_entities(jsonlogic))

    def get_component(self, jsonlogic):
        return next(self.query_entities(jsonlogic))

    def get_by_id(self, id):
        clause = {"==":[{"var":"id"}, id]}
        return next(self.get_component(clause), 
                    self.get_entity(clause),
                    self.get_package(clause))

    def parse(self, json):
        for constructor in self.constructors:
            if constructor.can_parse(json):
                return constructor(self, **json)

class MemSpace(Space):
    def __init__(self, pkgcls, entitycls, compcls, litcls, refcls):
        super().__init__(pkgcls, entitycls, compcls, litcls, refcls)
        self._packages = {}
        self._entities = {}
        self._components = {}

    def _iter_packages(self):
        for pkg in self._packages.values():
            yield pkg

    def _iter_entities(self):
        for entity in self._entities.values():
            yield entity
        
    def _iter_components(self):
        for component in self._components.values():
            yield component 

    def put_package(self, json):
        return self._put(json, self._packages)
    
    def put_entity(self, json):
        return self._put(json, self._entities)

    def put_component(self, json):
        return self._put(json, self._components)
    
    def _put(self, json, dataset):
        assert json.get('id')
        dataset[json.get('id')] = json
        return json

def match(**kwargs):
    return {"and":[{"==":[{"var":k}, v]} for (k,v) in kwargs.items()]}

class Base(ABC):
    def __init__(self, space, **kwargs):
        self.space = space

    def clone(self, **kwargs):
        return self.__class__(self.space, **kwargs)

    @abstractmethod
    def to_json(self):
        """
        Concrete subclasses should return a Python dictionary representing
        their JSON serialization. 
        """

    @abstractclassmethod
    def can_parse(json):
        """
        returns a boolean whether this class can parse the given JSON input. Used for factory methods. 
        NOTE: Experimental. May need to be culled. 
        """
    
class SRoot(Base):
    def __init__(self, space, **kwargs):
        super().__init__(space)
        self.id = kwargs.get('id') or str(uuid.uuid1())
        self.name = kwargs.get('name') or None
        self.types = set(kwargs.get('types') or [])
        self._packages = set(kwargs.get("packages") or [])
        self._entities = set(kwargs.get("entities") or [])
        self._components = set(kwargs.get("components") or [])
        self.put()
    
    @abstractmethod
    def put(self):
        """
        Concrete subclasses should implement a method that calls the appropriate
        put() method of the containing Space. 
        """

    def packages(self, jsonlogic = True):
        return self.space.query_packages({"and":[{"in":[{"var":"id"}, self._packages]}, jsonlogic]})

    def entities(self, jsonlogic = True):
        return self.space.query_entities({"and":[{"in":[{"var":"id"}, self._entities]}, jsonlogic]})

    def components(self, jsonlogic = True):
        return self.space.query_components({"and":[{"in":[{"var":"id"}, self._components]}, jsonlogic]})

    def clone(self, **kwargs):
        json = {**self.to_json(), **kwargs}
        assert json.get('id') != self.id
        return super().clone(**json)

    def to_json(self):
        return {"id":self.id, "types":list(self.types), "name":self.name}
    
    @classmethod
    def can_parse(json):
        keys = json.keys()
        return "id" in keys and "types" in keys
    
    def __repr__(self):
        return "%s(%s)"%(self.__class__.__name__, self.id)

    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)


class SEntity(SRoot):
    def put(self):
        return self.space.put_entity(self.to_json())

    def to_json(self):
        return {**super().to_json(), **{"packages":list(self._packages), "components":list(self._components)}}

    @classmethod
    def can_parse(self, json):
        keys = json.keys()
        return super().can_parse(json) and "packages" in keys and "components" in keys()

class SComponent(SRoot):
    def __init__(self, space, **kwargs):
        self.contents = kwargs.get("contents") or None
        super().__init__(space, **kwargs)

    def put(self):
        return self.space.put_component(self.to_json())

    def to_json(self):
        return {**super().to_json(), **{"packages":list(self._packages), "entities":list(self._entities), "contents":self.contents}}
 

class SPackage(SRoot):
    def put(self):
        return self.space.put_package(self.to_json())

    def to_json(self):
        return {**super().to_json(), **{"entities":list(self._entities), "components":list(self._components)}}
    
    @classmethod
    def can_parse(self, json):
        keys = json.keys()
        return super().can_parse(json) and "entities" in keys and "components" in keys()
        
    def add_entity(self, *entities): 
        for entity in entities:
            self._entities.add(entity.id)
            entity._packages.add(self.id)
        self.put()
        entity.put()
        return entity

    def add_component(self, component, *entities):
        for entity in entities:
            self._entities.add(entity.id)
            self._components.add(component.id)
            entity._components.add(component.id)
            entity._packages.add(self.id)
            component._entities.add(entity.id)
            component._packages.add(self.id)
        self.put()
        entity.put()
        component.put()
        return component

    def link(self, e1 : 'SEntity', e2 : 'SEntity', **kwargs) -> 'Halflink':
        left = self.add_component(SComponent(self.space, **kwargs), e1)
        right = self.add_component(SComponent(self.space, **kwargs), e2)

class Contents(Base):
    def __init__(self, space, value, type = "xsd:string"):
        self._space = space
        self._value = value 
        self._type = type

    @abstractmethod
    def to_json(self):
        """
        Concrete subclasses should return a typed JSON-LD representation of their contents
        """
    def value(self):
        return self._value

    def type(self):
        return self._type
    
    def clone(self):
        return self.__class__(self.space, self.value(), self.type())

    def __repr__(self):
        return "%s[%s]"%(self.type() or "?", self.value())
    
    def __eq__(self, other):
        return isinstance(other, Contents) and self.value() == other.value()
    
    def __hash__(self):
        return hash(self.value())

class Literal(Contents):
    def to_json(self):
        return {"value":self.value(), "types":self.type()}

    @classmethod
    def can_parse(json):
        keys = json.keys()
        return super().can_parse(json) and "value" in keys
        
class Ref(Contents):
    
    def to_json(self):
        return {"id":self._value, "types":"id"}
    
    def value(self) -> 'Entity':
        result = self.space.get_by_id(self.value())
        if isinstance(result, Ref):
            return result.get()
        else:
            return result


class HalfLink(Ref):
    def __init__(self, opposite, type = None):
        super().__init__(opposite)
        self.type = "HalfLink"

    def get(self) -> 'Entity':
        opposite = Root.get(self.value)
        return next(iter(opposite.entities()))

U = MemSpace(SPackage, SEntity, SComponent, Literal, Ref)

P = SPackage(U, id="SPackage", types = ["SPackage"], entities=["SEntity"], components=["SComponent"])
E = SEntity(U, id="SEntity", types = ["SEntity"], name = "SEntity", packages = ["SPackage"], components=["SComponent"])
C = SComponent(U, id="SComponent", types = ["SComponent"], name = "SComponent", packages = ["SPackage"], entities=["SEntity"])

"""
E2 = E.clone(id = "E2")
P.link(E, E2, contents = "Im a link")

P = SPackage(U, id="SPackage")
E = SEntity(U, id="SEntity")
C = SComponent(U, id="SComponent")

P.add_component(SComponent(U, id="SPackage", name="clones"), E)
P.add_component(SComponent(U, id="SEntity", name="clones"), E)
P.add_component(SComponent(U, id="SComponent", name="clones"), E)
"""

# Everything above this line is an experiment that may be thrown away.
# ---------------------------------------------------------------------------
class CompositeSpace(Space):
    """
    A space that facades multiple spaces.
    """
    def __init__(self):
        super().__init__()
        self._spaces = set([])
    
    def get(self, id):
        for space in self._spaces:
            yield space.get(id)
    
    def put(self, id, payload):
        for space in self._spaces:
            yield space.put(id, payload)

    
    def add_space(self, space):
        return self._spaces.add(space)
    
    def remove_space(self, space):
        return self._spaces.discard(space)

"""


class Root:
    assets = {}
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or str(uuid.uuid1())
        self.name = kwargs.get('name') or None
        self.types = set(kwargs.get('types') or [])
        self.__class__.put(self)

    @classmethod
    def get(cls, id):
        return cls.assets.get(id)
    
    @classmethod
    def put(cls, asset):
        cls.assets[asset.id] = asset
    
    @classmethod
    def delete(cls, id):
        del cls.assets[id]

    @classmethod
    def has(self, id):
        return bool(self.get(id))

    def clone(self):
        return self.__class__(name = self.name, types = self.types)

    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

    def json(self):
        return {"@id":self.id, "@type":list(self.types), "name":self.name}

    def __repr__(self):
        return "%s(name='%s')"%(self.__class__.__name__, self.name)
    
    def _get(self, resultset, name = None, id = None):
        if name or id:
            for item in resultset:
                if item.name == name or item.id == id:
                    return  item
        else:
            return resultset



class Entity(Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._packages = set([])
        self._components = set([])

    def components(self, name = None, id = None):  
        return self._get(self._components, name, id)
    
    def packages(self, name = None, id = None):  
        return self._get(self._packages, name, id)


    def json(self):
        return {**super().json(), 
                **{"packages":[{"@id":id} for id in self.packages]}, 
                **{"components":[{"@id":id} for id in self.components]}}




class Component(Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entities = set([])
        self._packages = set([])
        self.contents = None

    def entities(self, name = None, id = None):  
        return self._get(self._entities, name, id)
    
    def packages(self, name = None, id = None):  
        return self._get(self._packages, name, id)

    def get(self):
        return self.contents.get() if self.contents else None

    def set(self, contents : 'Contents'):
        self.contents = contents
        self.contents.set_owner(self)
        return self

    def clone(self):
        new = super().clone()
        new._packages = self._packages
        new._entities = self._entities
        new.contents = self.contents.clone()
        return new 

    def json(self):
        return {**super().json(), **{"contents":self.contents.to_json()}}


class Package(Root):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entities = set([])
        self._components = set([]) 
    
    def components(self, name = None, id = None):  
        return self._get(self._components, name, id)

    def add_component(self, component : Component, *entities) -> Component:
        for entity in self.add_entities(*entities):
            #self._entities.add(entity)
            self._components.add(component)
            #entity._packages.add(self)
            entity._components.add(component)
            component._entities.add(entity)
            component._packages.add(self)
        return component

    def entities(self, name = None, id = None):  
        return self._get(self._entities, name, id)
    
    def add_entities(self, *entities) -> List[Entity]:
        for entity in entities:
            entity = Root.get(entity.id) or entity
            self._entities.add(entity)
            entity._packages.add(self)
        return entities

    def link(self, e1 : Entity, e2 : Entity, **kwargs) -> HalfLink:
        left = self.add_component(Component(**kwargs), e1)
        right = self.add_component(Component(**kwargs), e2)

        left.set(HalfLink(right.id))
        right.set(HalfLink(left.id))
        return left

    def clone(self, e : Entity, pkg : 'Package' = None, by_reference = False) -> Entity:
        new = (self.get(e.id) or e).clone()
        self.add_component(Component(name="extends"), new).set(Ref(e.id))
        for comp in e.components():
            if pkg and not pkg in comp._packages:
                continue
            contents = Ref(comp.id) if by_reference else comp.contents.clone()
            self.add_component(Component(name=comp.name).set(contents), new)
        return new

  
######################################
### Feature Demo  -  Making a Door ###
######################################
# Create a new Package representing a small massing study
mpkg = Package(name = "massing")


# Next, we create a single entity, a door
standard_door = Entity(name="standard-door")

# Within the context of the massing Package, we add two Components, representing the width and height of the door
mpkg.add_component(Component(name="width"), standard_door).set(Contents(value=5, type="ifc5:units/meter"))
mpkg.add_component(Component(name="height"), standard_door).set(Contents(value=10, type="ifc5:units/meter"))

mpkg.add_component(Component(name="color"), standard_door).set(Contents(value=[0.5, 0.25, 0.75], type="ifc5:colourrgb"))

# Now we can list the entities in the massing package
mpkg.entities()
# >>> {Entity(name='standard-door')}

# Retrieve a single entity by id or name
assert mpkg.entities(name='standard-door') == standard_door

# View its components
print(mpkg.entities(name='standard-door').components())
# >>> {Component(name='width'), Component(name='color'), Component(name='height')}

# And fetch or set the value of, say, its width
mpkg.entities(name='standard-door').components(name='width').get() == 5


assert mpkg.entities(name='standard-door').components(name='width').set(Contents(value=4.5, type="ifc5:units/meter")).get() == 4.5

# Now we create a new entity, representing the door knob of the door
knob = Entity(name="knob-1", types=["ifc5:door/knob"])

# Now we link the knob and door knob through a decomposition relationship, which returns the outgoing edge of the link
print(mpkg.link(standard_door, knob, types=["ifc5:decomposes"], name="door-knob-decomposition"))
# >>> Component(name='door-knob-decomposition')

# With the link established, we can now traverse from the door to the door knob automatically. 
# All intermediate components are skipped over, making it appear that the entities are linked directly to each other.
assert mpkg.entities(name="standard-door").components(name='door-knob-decomposition').get() == knob


# Links are bidirectional, so we can also return back to the door itself.
assert mpkg.entities(name="standard-door").components(name='door-knob-decomposition').get().components(name='door-knob-decomposition').get() == standard_door


# Now let's make the door knob color match the door's color. 
mpkg.add_component(mpkg.entities(name="standard-door").components(name='color'), mpkg.entities(name='knob-1'))
assert mpkg.entities(name='knob-1').components(name='color').get() == [0.5, 0.25, 0.75]

# Note that changing the color of the door changes the color of the knob, because the "color" Component is shared by reference.
mpkg.entities(name="standard-door").components(name='color').set(Contents(value=[1, 1, 1], type="ifc5:colourrgb"))
assert mpkg.entities(name='knob-1').components(name='color').get() == [1, 1, 1]


# It is also possible for the same entity to belong to more than one package
dpkg = Package(name="design")
dpkg.add_entities(knob)
assert mpkg.entities(name="knob-1") == dpkg.entities(name="knob-1")

#############################################
### Feature Demo  -  Cloning and Modeling ###
#############################################

# Packages support the ability to clone existing Entities and their Components. We can use cloning to copy existing entities (as a starting point),
# or as a kind of template. 

# Let's clone the 'standard-door' Entity form the last section. This creates a new door we'll call "door-1".
door1 = dpkg.clone(standard_door)
door1.name = 'door-1'

# door-1 is a new Entity that contains _copies_ of all the same Components 'standard-door' had. 

assert door1.components(name='color').get() == standard_door.components(name='color').get()
assert door1.components(name='width').get() == standard_door.components(name='width').get()
assert door1.components(name='height').get() == standard_door.components(name='height').get()

# Let's go ahead and change door-1's color. Because door-1 has a copy of standard-door's Components, standard-door's color remains unchanged.
door1.components(name='color').set(Contents('blue', 'ifc5:namedcolor'))
assert door1.components(name='color').get() == 'blue'
assert standard_door.components(name='color').get() == [1, 1, 1]

# We can also clone Entities "by reference". Rather than creating copies of a cloned Entity's Components, each Component in the clone
# is replaced with a reference ("Ref") Component back to the original Component. This allows all clones share common Components, and behavior
# more like instances of a common class. 

#Let's create another clone of standard-door "by reference", named door-2.
door2 = dpkg.clone(standard_door, by_reference=True) 
door2.name = 'door-2'

# door-2's color is references standard-door's color, instead of storing its own copy.
assert door2.components(name='color').get() == standard_door.components(name='color').get()

# If we update standard-door's color
standard_door.components(name='color').set(Contents(value=[0.5,0.5,0.5], type="ifc5:colourgb"))

# door-2 immediately sees the change. Any other clone sharing standard-door's color Component "by reference" would as well. 
assert door2.components(name='color').get() == standard_door.components(name='color').get()

# This "by reference" cloning is just a starting point. Nothing would stop us from then replacing door-2's color with its own Component:
door2.components(name='color').set(Contents(value='green', type='ifc5:namedcolor'))
assert door2.components(name='color').get() != standard_door.components(name='color').get()

# door-2 can then be further cloned to arbitrary depths. The cloning lineage is preserved through a special Components, "extends",
# that is attached to every clone on creation.

# This basic cloning mechanism provides a foundation for building Packages of predefined Entities that stakeholders can then clone
# from as the basis of their work. Those clones can be further enhanced and shared back for further cloning.

"""
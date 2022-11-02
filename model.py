
import uuid
import json
from typing import List
from json_logic import jsonLogic as logic

class Space:
    """
    As in, "address space". Spaces are an abstraction of an address layer, and not part of the serialization format.

    Note that an address space is different from a dedicated storage layer. A space is a mechanism to look something up.
    Individual results may come from different locations based on the ID. The dispatch strategy is left to the Space implementation.

    # All of these operations are intentionally idempotent.
    """
    # Because this isn't part of the serialization format, maybe a good place to enact notifications.
    
    def __init__(self, pkgcls, entitycls, compcls):
        self.Package = pkgcls
        self.Entity = entitycls
        self.Component = compcls

    def _query_all(self):
        raise NotImplementedError("Concrete subclasses must implement")

    def _query(self, jsonlogic):
        for asset in self._query_all():
            if logic.apply(jsonlogic, asset):
                yield asset

    def query_packages(self, **kwargs):
        for result in self._query(kwargs):
            yield self.Package(self, **result)

    def query_entities(self, **kwargs):
        for result in self._query(kwargs):
            yield self.Entity(self, **result)

    def query_components(self, **kwargs):
        for result in self._query(kwargs):
            yield self.Component(self, **result)

    def get_package(self, **kwargs):
        return next(self.query_packages(**kwargs))
    
    def get_entity(self, **kwargs):
        return next(self.query_entities(**kwargs))

    def get_component(self, **kwargs):
        return next(self.query_entities(**kwargs))

    def _put(self, json):
        raise NotImplementedError("Concrete subclasses must implement")

    def put_package(self, pkg):
        return self._put(pkg.json())

    def put_entity(self, entity):
        return self._put(entity.json())

    def put_component(self, component):
        return self._put(component.json())


class MemSpace(Space):
    def __init__(self):
        self.res = {}

    def _query_all(self):
        return self.res.values()
        
    def _put(self, payload):
        assert payload.get('id')
        self.res[payload.get('id')] = payload
        return payload


class SRoot:
    def __init__(self, space, **kwargs):
        self.space = space
        self.id = kwargs.get('id') or str(uuid.uuid1())
        self.name = kwargs.get('name') or None
        self.types = set(kwargs.get('types') or [])
        self.put()
    
    def put(self):
        raise NotImplementedError("Concrete subclasses must implement")

    def clone(self, **kwargs):
        json = {**self.json(), **kwargs}
        assert json.get('id') != self.id
        return self.__class__(self.space, **json)

    def json(self):
        return {"id":self.id, "types":list(self.types), "index":self.name}
    
    def __repr__(self):
        return "%s(%s)"%(self.__class__.__name__, self.id)

    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

    def _find(self, set, name = None):
        for id in set:
            item = self.space.get(id)
            print
            if "SPackage" in item.get('types'): # FIXME
                item = SPackage(self.space, **item)
            elif "SEntity" in item.get('types'):
                item = SEntity(self.space, **item)
            elif "SComponent" in item.get('types'):
                item = SComponent(self.space, **item)
            if name and item.name == name:
                return item
            else:
                yield item
        
class SEntity(SRoot):
    def __init__(self, space, **kwargs):
        self._packages = set(kwargs.get("packages") or [])
        self._components = set(kwargs.get("components") or [])
        super().__init__(space, **kwargs)

    def json(self):
        return {**super().json(), **{"packages":list(self._packages), "components":list(self._components)}}
    
    def packages(self, **kwargs):
        return self.space.query_packages(self._packages, **kwargs)

    def components(self, name= None):
        return self.space.query_component(self)

class SComponent(SRoot):
    def __init__(self, space, **kwargs):
        self._packages = set(kwargs.get("packages") or [])
        self._entities = set(kwargs.get("entities") or [])
        self.contents = kwargs.get("contents") or None
        super().__init__(space, **kwargs)

    def json(self):
        return {**super().json(), **{"packages":list(self._packages), "entities":list(self._entities)}}
 
    def packages(self, name = None):
        return self._find(self._packages, name)

    def entities(self, name = None):
        return self._find(self._entities, name)


class SPackage(SRoot):
    def __init__(self, space, **kwargs):
        self._entities = set(kwargs.get("entities") or [])
        self._components = set(kwargs.get("components") or [])
        super().__init__(space, **kwargs)

    def json(self):
        return {**super().json(), **{"entities":list(self._entities), "components":list(self._components)}}
    
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

    def entities(self, name = None):
        return self._find(self._entities, name)

    def components(self, name = None):
        return self._find(self._components, name)

    def link(self, e1 : 'SEntity', e2 : 'SEntity', **kwargs) -> 'Halflink':
        left = self.add_component(SComponent(self.space, **kwargs), e1)
        right = self.add_component(SComponent(self.space, **kwargs), e2)

    

U = MemSpace()

P = SPackage(U, id="SPackage", types = ["SPackage"], entities=["SEntity"], components=["SComponent"])
E = SEntity(U, id="SEntity", types = ["SEntity"], name = "SEntity", packages = ["SPackage"], components=["SComponent"])
C = SComponent(U, id="SComponent", types = ["SComponent"], name = "SComponent", packages = ["SPackage"], entities=["SEntity"])

E2 = E.clone(id = "E2")
P.link(E, E2, contents = "Im a link")
"""
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

class Contents:
    def __init__(self, value, type):
        self.value = value
        self.type = type
        self.owner = None

    def set_owner(self, owner):
        self.owner = owner

    def json(self):
        return {"@value":self.value, "@type":self.type}

    def __repr__(self):
        return "%s[%s]"%(self.type or "?", self.value)

    def clone(self):
        return self.__class__(self.value, self.type)

    def get(self):
        return self.value


class Ref(Contents):
    def __init__(self, target, type = None):
        super().__init__(target, "Ref")
    
    def json(self):
        return {"@id":self.value}
    
    def get(self) -> 'Entity':
        result = Root.get(self.value).get()
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
        return {**super().json(), **{"contents":self.contents.json()}}


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
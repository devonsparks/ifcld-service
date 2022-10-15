
import uuid
import json
from typing import List

class Contents:
    def __init__(self, value, type):
        self.value = value
        self.type = type

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
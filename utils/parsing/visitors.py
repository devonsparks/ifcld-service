from abc import ABCMeta, abstractmethod

class IVisitor(object):
    __metaclass__ = ABCMeta
    @abstractmethod
    def visit(self, client, file, offset):
        raise NotImplementedError


class FileVisitor(IVisitor):
    def visit(self, client, file):
        client.beginFile(file, 0)
        for i, section in enumerate(file.sections):
            SectionVisitor().visit(client, section, i)
        client.endFile(file, 0)


class SectionVisitor(IVisitor):
    def visit(self, client, section, offset):
        client.beginSection(section, offset)
        for i, entity in enumerate(section.entities):
            if hasattr(entity, 'type_name'):
               SimpleEntityVisitor().visit(client,  entity, i)  
            else:
                raise Exception("A complex STEP entity with no distinct type name was found. No logic built to support this condition. Please raise an issue on Github, along with your example, if you believe this case should be addressed")
        client.endSection(section, offset)


class SimpleEntityVisitor(IVisitor):
    def visit(self, client, entity, offset):
        client.beginEntity(entity, offset) 
        for i, param in enumerate(entity.params):
            SimpleParameterVisitor().visit(client, param, i)
        client.endEntity(entity, offset)


class SimpleParameterVisitor(IVisitor):
    def visit(self, client,  param, offset):
        client.beginParameter(param, offset)
        client.endParameter(param, offset)
        
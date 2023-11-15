
class IClient(object):

    def beginFile(self, file, offset):
        pass

    def beginSection(self, section, offset):
        pass

    def beginEntity(self, entity, offset):
        pass

    def beginParameter(self, param, offset):
        pass

    def endFile(self, file, offset):
        pass
    
    def endSection(self, section, offset):
        pass

    def endEntity(self, entity, offset):
        pass

    def endParameter(self, param, offset):
        pass

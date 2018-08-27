from visa import ResourceManager

class GenericInstrument(object):
	def __init__(self,address):
		self.address = address
		self.initialise()


	def initialise(self):
		rm = ResourceManager()
		self.handle = rm.open_resource(self.address)

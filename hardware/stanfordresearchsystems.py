from .instrument import GenericInstrument


class SIM900(GenericInstrument):
	def __init__(self,address):
		super(SIM900,self).__init__(address)
		self.handle.read_termination = '\r\n'


	def initialise(self):
		super(SIM900,self).initialise()
		self.clear()


	def clear(self):
		self.handle.clear()
		self.handle.write('*CLS')
		self.prepend = ''
		self.escstr = 'xyx'
		self.active_module = None


	def ask(self,slot,query):
		self.switch_to(slot)
		return self.handle.ask(query)


	def write(self,slot,text):
		self.switch_to(slot)
		self.handle.write(text)


	def read(self,slot):
		self.switch_to(slot)
		return self.handle.read()


	def switch_to(self,slot):
		if self.active_module != slot:
			self.handle.write('{}CONN {}, "{}"'.format(self.prepend,slot,self.escstr))
			self.prepend = self.escstr
			self.active_module = slot

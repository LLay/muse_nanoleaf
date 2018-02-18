from ola.ClientWrapper import ClientWrapper
from Orcan2 import Orcan2, Mode
from StoppableThread import StoppableThread
import array

class Orcan2LightManager:

	def DmxSent(self, state):
	  print(state)
	  print(state.Succeeded())
	  if not state.Succeeded() or self.thread.stopped():
	    self.clientWrapper.Stop()

	UNIVERSE_DEFAULT = 1
	TICK_INTERVAL_DEFAULT = 10  # in ms

	def __init__(self, clientWrapper = ClientWrapper(), light = Orcan2(), universe = UNIVERSE_DEFAULT, tickInterval = TICK_INTERVAL_DEFAULT):
		self.clientWrapper = clientWrapper
		self.client = clientWrapper.Client()
		self.light = light
		self.universe = universe
		self.tickInterval = tickInterval
		self.thread = None

	def updateLight(self, **kwargs):
		self.light.update(kwargs)

	def SendDMXFrame(self):
		self.clientWrapper.AddEvent(self.tickInterval, self.SendDMXFrame)
		lightState = self.wrapArrayState(self.light.getStateAsArray())
		self.client.SendDmx(self.universe, lightState, self.DmxSent)

	def wrapArrayState(self, state):
		return array.array('B', state)

	def run(self, thread):
		self.thread = thread
		self.clientWrapper.AddEvent(self.tickInterval, self.SendDMXFrame)
		self.clientWrapper.Run()
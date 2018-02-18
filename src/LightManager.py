from ola.ClientWrapper import ClientWrapper
from Orcan2 import Orcan2, Mode
from StoppableThread import StoppableThread
import array

class Orcan2LightManager:

    def DmxSent(self, state):
      if not state.Succeeded() or self.thread.stopped():
        self.clientWrapper.Stop()

    UNIVERSE_DEFAULT = 1
    TICK_INTERVAL_DEFAULT = 10  # in ms
    LIGHT_ADDRESS = 0
    LIGHT_INSTANCE = 1

    def __init__(self, clientWrapper = ClientWrapper(), lightAddress = 1, light = Orcan2(), universe = UNIVERSE_DEFAULT, tickInterval = TICK_INTERVAL_DEFAULT):
        self.clientWrapper = clientWrapper
        self.client = clientWrapper.Client()
        self.lights = {}
        self.lights[lightAddress] = light
        self.universe = universe
        self.tickInterval = tickInterval
        self.thread = None


    def createLightGroup(self, address, clazz):
        self.lights[address] = clazz()
        return self.lights[address]

    def getLightGroup(self, address):    
        return self.lights[address]

    def SendDMXFrame(self):
        self.clientWrapper.AddEvent(self.tickInterval, self.SendDMXFrame)
        #lightState = self.wrapArrayState(self.getLightStatesAsArrays())
        lightState = self.wrapArrayState(self.getLightStatesAsArrays())
        self.client.SendDmx(self.universe, lightState, self.DmxSent)

    def getLightStatesAsArrays(self):
        #TODO Think about optimization here
        orderedLightGroups = self.getLightGroupsOrderedByAddress()
        print(orderedLightGroups)
        lightArray = [0]*512
        for address,  lightGroup in orderedLightGroups:
            lightGroupState = lightGroup.getStateAsArray()
            for offset in range(len(lightGroupState)):
                lightArray[address+offset-1] = lightGroupState[offset]
        print(lightArray)
        return lightArray

    def getLightGroupsOrderedByAddress(self):
        orderedLights = list(self.lights.iteritems())
        orderedLights = sorted(orderedLights,key = lambda t: t[0])
        return orderedLights

    def wrapArrayState(self, state):
        return array.array('B', state)

    def run(self, thread):
        self.thread = thread
        self.clientWrapper.AddEvent(self.tickInterval, self.SendDMXFrame)
        self.clientWrapper.Run()

    # _instance = None
 #    def __new__(cls, *args, **kwargs):
    #     if not cls._instance:
 #            cls._instance = super(Orcan2LightManager, cls).__new__(
 #                                cls, *args, **kwargs)
 #        return cls._instance

from ola.ClientWrapper import ClientWrapper
from Orcan2 import Orcan2, Mode
from StoppableThread import StoppableThread
import array
import sys


class DMXLightManager:
    def DmxSent(self, state):
      if not state.Succeeded() or self.thread.stopped():
        self.clientWrapper.Stop()
        sys.exit()
        
    UNIVERSE_DEFAULT = 1
    TICK_INTERVAL_DEFAULT = 10  # in ms
    LIGHT_ADDRESS = 0
    LIGHT_INSTANCE = 1
    NUM_BYTES_PER_LIGHT = 8

    def __init__(self, clientWrapper = ClientWrapper(), lightAddress = None, light = None, universe = UNIVERSE_DEFAULT, tickInterval = TICK_INTERVAL_DEFAULT):
        self.clientWrapper = clientWrapper
        self.client = clientWrapper.Client()
        self.lights = {}
        if lightAddress and light:
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
        lightState = self.wrapArrayState(self.getLightStatesAsArrays())
        self.client.SendDmx(self.universe, lightState, self.DmxSent)

    def getLightStatesAsArrays(self):
        #TODO Think about optimization here
        orderedLightGroups = self.getLightGroupsOrderedByAddress()
        arraySize = orderedLightGroups[-1][Orcan2LightManager.LIGHT_ADDRESS] + Orcan2LightManager.NUM_BYTES_PER_LIGHT
        lightArray = [0]*arraySize
        for address,  lightGroup in orderedLightGroups:
            lightGroupState = lightGroup.getStateAsArray()
            for offset in range(len(lightGroupState)):
                lightArray[address+offset-1] = lightGroupState[offset]
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

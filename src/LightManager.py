from ola.ClientWrapper import ClientWrapper
from Orcan2 import Orcan2, Mode
from StoppableThread import StoppableThread

import array
import sys
import colorsys

sys.path.insert(0, '/Users/lay/workspace/dmx-lib/muse_controller/nanoleafpy2')
from nanoleaf import setup, Aurora

rgbToHSB(r,g,b):
    h,s,v = colorsys.rgb_to_hsv(r,g,b)
    # h,l,s = colorsys.rgb_to_hls(r,g,b)

ANIMATION_ID = "myanimation"

class NanoleafLightManager:
    def __init__(self):
        print "Retrieving auroras..."
        ipAddressList = setup.find_auroras()
        print "Auroras found:", ipAddressList

        # print "Selecting only whitelisted auroras..."
        # ipWhitelist = []
        # ipAddressList = [x for x in ipAddressList if x in ipWhitelist]
        # print "Auroras used:", ipAddressList

        print "Retrieving auth tokens..."
        ipAuthMap = {}
        for ip in ipAddressList:
            ipAuthMap[ip] = setup.generate_auth_token(ip)
        print "Tokens generated:", ipAuthMap

        print "Instatiating Aurora Objects..."
        self.auroras = []
        for ip in ipAuthMap:
            self.auroras += [{'aurora': Aurora(ip, ipAuthMap[ip])}]
        print "Finished Instatiating Aurora Objects..."

        print "Initiating Aurora Metadata..."
        self.auroras = {}
        for aurora in self.auroras:
            aurora['panelIDs'] = [x.panelId for x in self.aurora.panel_positions()]

        print "Finished Initiating Aurora Metadata..."

        print "Turning on Auroras"
        for aurora in self.auroras:
            aurora['aurora'].on = True
        my_aurora.effect = ANIMATION_ID
        print "Finished Turning on Auroras"

        print "Setting lights to white"
        self.updateLights(255, 255, 255, 100)
        print "Finished setting lights to white"

    def updateLights(r, g, b, brightness):
        # h,s,b = colorsys.rgb_to_hsv(r,g,b) # Assuming value == brightness

        # TODO Modify RGB values by brightness. Experimental:
        # r = r * brightness / 100
        # g = g * brightness / 100
        # b = b * brightness / 100

        # CASE 1 - update at 100fps
        #  - set the god damn color
        for aurora in self.auroras:
            effect = self.getStaticEffect(aurora, r,g,b)
            aurora.effect_set_raw(effect)

        # CASE 2 - sample at once every 2 seconds. Ensure aurora is all one color within 2 seconds so that we can transition smoothly
        # get current lights state/color
        # transition between them

        # CASE 3 - Same as case 2, except use the flow animation for the transition

    def getStaticEffect(self, aurora, r, g, b):
        panelIDs = aurora['panelIDs']
        numFrames = 1
        transitionTime = 1 # Decaseconds

        # animData is of the form: <numPanels> <panelId0> <numFrames0> <RGBWT01> <RGBWT02> ... <RGBWT0n(0)> <panelId1> <numFrames1> <RGBWT11> <RGBWT12> ... <RGBWT1n(1)> ... ... <panelIdN> <numFramesN> <RGBWTN1> <RGBWTN2> ... <RGBWTNn(N)>
        animData = "%d " % (len(panelIDs))
        for panelID in panelIDs:
            animData += "%d, %d, %d, %d, %d, 0, %d " % (panelID, numFrames, r, g, b, 0, transitionTime)

        return {
            "command": "add",
            "animName": ANIMATION_ID,
            "animType": "static",
            "animData": animData,
            "loop": False
        }

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
        arraySize = orderedLightGroups[-1][DMXLightManager.LIGHT_ADDRESS] + DMXLightManager.NUM_BYTES_PER_LIGHT
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

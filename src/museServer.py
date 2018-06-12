from liblo import *
from threading import Thread

import math
import numpy as np
import random
import sys
import time
import traceback
import urllib2

from LightManager import DMXLightManager, NanoleafLightManager
from LightMixer import EEGWaveLightMixer
from MovingAverage import MovingAverageExponential, MovingAverageLinear
from StoppableThread import StoppableThread
from MuseState import MuseState
import Config as config

# TODO make the nanoleafpy2 a propers dependency
# TODO make the connection to nanoleaf an option. when you run the program there
# should be an option to search for and connect to existing nanoleaf installations
# Then it should store the ips and auth tokent for these installations in some
# persistant store.
# If the option is not specified, this program should try to read from said persistant store
#
# TODO Finish gutting DMX logic, and any extra abstraction that is no longer needed
# Make the threading a little easier to use?

def avg(*values):
    return reduce(lambda x, y: x + y, values) / len(values)

# Wrapper for NanoleafLightManager
class NanoleafClient():
    def __init__(self):
        self.lightManager = NanoleafLightManager()

    def updateLights(self, color):
        self.lightManager.updateLights(color.r, color.g, color.b, color.brightness)

    def kill(self):
        self.lightManager.kill()

receivingMessages = True
timeSinceLastSecond = 1
class MuseServer(ServerThread):

    def __init__(self):
        # Listen on port 5001
        ServerThread.__init__(self, 5001)
        MovingAverageChoice = MovingAverageExponential
        self.alpha_relative_rolling_avg_generator = MovingAverageChoice(config.ROLLING_EEG_WINDOW)
        self.beta_relative_rolling_avg_generator = MovingAverageChoice(config.ROLLING_EEG_WINDOW)
        self.delta_relative_rolling_avg_generator = MovingAverageChoice(config.ROLLING_EEG_WINDOW)
        self.gamma_relative_rolling_avg_generator = MovingAverageChoice(config.ROLLING_EEG_WINDOW)
        self.theta_relative_rolling_avg_generator = MovingAverageChoice(config.ROLLING_EEG_WINDOW)

        self.all_contacts_mean = MovingAverageChoice(config.CONTACT_LOS_TIMEOUT)

        self.state = MuseState()

        self.connections_debug = (0, 0, 0, 0)

        self.lightServerThreadNanoleaf = StoppableThread(self.serveNanoleafLights)
        self.lightServerThreadNanoleaf.start()
        self.globalMixer = None

        # Fake input
        self.state.alpha = .32
        self.state.beta = .32
        self.state.delta = .32
        self.state.gamma = .32
        self.state.theta = .32
        self.connectThread = StoppableThread(self.connectToggle)
        self.connectThread.start()

    def connectToggle(self, thread):
        self.state.connected = 1
        self.state.touching_forehead = 1
        while not thread.stopped():
            self.state.alpha = random.random()
            self.state.beta = random.random()
            self.state.delta = random.random()
            self.state.gamma = random.random()
            self.state.theta = random.random()
            self.state.connected = abs(1-self.state.connected)
            self.state.touching_forehead = abs(1-self.state.touching_forehead)
            print( "connected", self.state.connected)
            time.sleep(10)
        sys.exit()

    def kill(self):
        self.lightServerThreadNanoleaf.stop()
        self.connectThread.stop()

    def serveNanoleafLights(self, thread):
        nanoleafClient = NanoleafClient()

        while not thread.stopped():
            try:
                light = self.globalMixer.getLight()
                nanoleafClient.updateLights(light)
                # print "Nanoleaf lights (from Mixer), COLORS: r: %d g: %d b: %d, BRIGHTNESS: %d" % (light.r, light.g, light.b, light.brightness)
                time.sleep(config.NANOLEAF_LIGHT_UPDATE_INTERVAL)

            except Exception, err:
                print "Exception in serveNanoleafLights: ", err.__class__.__name__, err.message
                nanoleafClient.kill()
                sys.exit()
        print "EXITING serveNanoleafLights"
        nanoleafClient.kill()
        sys.exit()

    # Dim the light over 2 seconds. Then as a precaution set their colors to black
    def dimLights(self, dmxClient):
        # number of decaseconds to fade
        fadeCount = 2000

        startEEGBright = dmxClient.lightManager.getLightGroup(config.EEG_LIGHT_GROUP_ADDRESS).brightness
        curEEGBright = startEEGBright
        startSpotBright = dmxClient.lightManager.getLightGroup(config.SPOTLIGHT_LIGHT_GROUP_ADDRESS).brightness
        curSpotBright = startSpotBright

        for _ in range(fadeCount):
            curEEGBright -= config.USER_LIGHT_BRIGHTNESS / float(fadeCount)
            curEEGBright = max(0,int(curEEGBright))
            dmxClient.updateLightGroupBrightness(config.EEG_LIGHT_GROUP_ADDRESS,curEEGBright)
            curSpotBright -= config.DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS / float(fadeCount)
            curSpotBright = max(0, int(curSpotBright))
            dmxClient.updateLightGroupBrightness(config.SPOTLIGHT_LIGHT_GROUP_ADDRESS, curSpotBright)
            if curEEGBright == curSpotBright ==  0:
                break
            time.sleep(0.01)

    # receive alpha data
    @make_method('/muse/elements/alpha_relative', 'ffff')
    def alpha_relative_callback(self, path, *args):
        weights = np.array([1,1])
        values = np.array(args[0])
        values = np.array(values[np.argsort(values)[-2:]])
        alphaWeightedAndNormalized = self.weighter(values, weights, normalizationMin = .05, normalizationMax=.5)
        x = self.alpha_relative_rolling_avg_generator.next(alphaWeightedAndNormalized)
        self.state.alpha = x if not math.isnan(x) else 0

    # receive beta data
    @make_method('/muse/elements/beta_relative', 'ffff')
    def beta_relative_callback(self, path, *args):
        weights = np.array([1,1])
        values = np.array(args[0])
        values = np.array(values[np.argsort(values)[-2:]])
        betaWeightedAndNormalized = self.weighter(values, weights, normalizationMin=.05, normalizationMax=.5)
        x = self.beta_relative_rolling_avg_generator.next(betaWeightedAndNormalized)
        self.state.beta = x if not math.isnan(x) else 0

    # receive gamma data
    @make_method('/muse/elements/gamma_relative', 'ffff')
    def gamma_relative_callback(self, path, *args):
        weights = [1]*4
        values = args[0]
        gammaWeightedAndNormalized = self.weighter(values, weights)
        x = self.gamma_relative_rolling_avg_generator.next(gammaWeightedAndNormalized)
        self.state.gamma = x if not math.isnan(x) else 0

    # receive delta data
    @make_method('/muse/elements/delta_relative', 'ffff')
    def delta_relative_callback(self, path, *args):
        weights = [1]*4
        values = args[0]
        deltaWeightedAndNormalized = self.weighter(values, weights)
        x = self.delta_relative_rolling_avg_generator.next(deltaWeightedAndNormalized)
        self.state.delta = x if not math.isnan(x) else 0

    # receive theta data
    @make_method('/muse/elements/theta_relative', 'ffff')
    def theta_relative_callback(self, path, *args):
        weights = [1]*4
        values = args[0]
        thetaWeightedAndNormalized = self.weighter(values, weights)
        x = self.theta_relative_rolling_avg_generator.next(thetaWeightedAndNormalized)
        self.state.theta = x if not math.isnan(x) else 0


    def weighter(self, values, weights, normalizationMin = 0, normalizationMax = 1):
        avgVal = np.nanmean(np.multiply(values,weights))
        if np.isnan(avgVal):
            return 0
        normalizedAvgVal = (avgVal - normalizationMin) / (normalizationMax - normalizationMin)
        normalizedAvgVal = max(0, normalizedAvgVal)
        normalizedAvgVal = min(1, normalizedAvgVal)
        return normalizedAvgVal

    @make_method('/muse/elements/touching_forehead', 'i')
    def horseshoe_callback(self, path, arg):
        global receivingMessages
        receivingMessages = True
        # TODO apparently this callback never gets called
        x = int(arg) if not math.isnan(arg[0]) else 0
        self.state.touching_forehead = x

    # horseshoe gives more granular information on which contacts have signal
    # from the brain
    # We get a tuple of 4 numbers, each representing the connectivity of
    # each contact 1 = good, 2 = ok, >=3 bad
    @make_method('/muse/elements/horseshoe', 'ffff')
    def horseshoe_callback(self, path, args):
        global receivingMessages
        receivingMessages = True
        # A score between 0 and 1 of how good the connections of the contacts are
        connectionScore = (8 - (sum(map(lambda x: x if x <= 3 else 3, args)) - 4)) / 8.0
        self.state.connectionScore = connectionScore

        if self.all_contacts_mean.next(connectionScore, printDebug=True) < 0.05 and self.state.connected:
            # It has been at least CONTACT_LOS_TIMEOUT seconds of total LOS on all contacts
            self.state.connected = 0
            print "LOST CONNECTION"

        if connectionScore > 0.5 and not self.state.connected:
            # This is the first time the user has put the muse on in at least CONTACT_LOS_TIMEOUT second
            print "CONNECTED!!"
            self.state.connected = 1

        # logging
        self.connections_debug = args
    #receive accelrometer data
    # @make_method('/muse/acc', 'fff')
    # def acc_callback(self, path, args):
    #     acc_x, acc_y, acc_z = args
    # print "%s %f %f %f" % (path, acc_x, acc_y, acc_z)

    #receive jaw clench
    # @make_method('/muse/elements/jaw_clench', 'f')
    # def jaw_clench_callback(self, path, args):
    #     x = args
    #     print "%s, %f" % (path, x[0])

    #receive blink
    # @make_method('/muse/elements/blink', 'f')
    # def blink_callback(self, path, args):
    #     x = args
    #     print "%s, %f" % (path, x[0])

    #receive EEG data
    # @make_method('/muse/eeg', 'ffff')
    # def eeg_callback(self, path, args):
    #     l_ear, l_forehead, r_forehead, r_ear = args
    #     print "%s %f %f %f %f" % (path, l_ear, l_forehead, r_forehead, r_ear)

    #handle unexpected messages
    # @make_method(None, None)
    # def fallback(self, path, args, types, src):
        # print "Unknown message \
        # \n\t Source: '%s' \
        # \n\t Address: '%s' \
        # \n\t Types: '%s ' \
        # \n\t Payload: '%s'" \
        # % (src.url, path, types, args)

try:
    server = MuseServer()
except ServerError, err:
    print str(err)
    sys.exit()

server.start()

if __name__ == "__main__":
    while 1:
        try:
            time.sleep(1)
            server
        except KeyboardInterrupt:
            server.kill()
            sys.exit()

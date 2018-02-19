from liblo import *

import sys
import time
import random
import traceback
import math
import numpy as np
from threading import Thread
from LightManager import DMXLightManager
from Orcan2 import Orcan2
from PTVWIRE import PTVWIRE
from LightMixer import LightMixer
from MovingAverage import MovingAverage
from StoppableThread import StoppableThread
from HelperClasses import MuseState

from guppy import hpy
h = hpy()

import urllib2

# How often we update the lights. Measured in seconds. Minimum of 0.1 (You can go lower, but we only get data from the muse at 10Hz)
LIGHT_UPDATE_INTERVAL = 0.01
# How often we internally render an new frame of the default animation
DEFAULT_ANIMATION_RENDER_RATE = 0.01
# Number of second over which we average eeg signals.
ROLLING_EEG_WINDOW = 3
# Number of second over which fade between user input and the default light animation.
USER_TO_DEFAULT_FADE_WINDOW = 5
# The delay in seconds between loss of signal on all contacts and ..doing something about it
CONTACT_LOS_TIMEOUT = 3
# the default brightness of the lights when the user is connected
DEFAULT_USER_BRIGHTNESS = 125

# Light group addresses
EEG_LIGHT_GROUP_ADDRESS= 1
SPOTLIGHT_LIGHT_GROUP_ADDRESS = 8

# How often to print the log message in seconds
LOG_PRINT_RATE = 1

# Correct decimal place for relevant values. Don't change me!
ROLLING_EEG_WINDOW *= 10
CONTACT_LOS_TIMEOUT *= 10

def avg(*values):
    return reduce(lambda x, y: x + y, values) / len(values)

class DMXClient():
    # @selectedLights (int array) Which lights this client talks to
    def __init__(self):
        self.lightManager = DMXLightManager(tickInterval=10)
        thread = StoppableThread(target = self.lightManager.run)
        thread.start()

    def createLightGroup(self, address, lightClass):
        self.lightManager.createLightGroup(address, lightClass)

    def updateLightGroup(self, address, color):
        self.updateLightGroupBrightness(address, color)
        self.updateLightGroupColor(address, color)

    def updateLightGroupBrightness(self, address, color):
        self.lightManager.getLightGroup(address).setRGB(int(color.r), int(color.g), int(color.b))

    def updateLightGroupColor(self, address, color):
        self.lightManager.getLightGroup(address).setBrightness(int(color.brightness))

    def kill(self):
        self.lightManager.thread.stop()
        #TODO Implement self.lightManager.kill()

class NodeLeafClient():
    pass

# MuseServer
class MuseServer(ServerThread):

    def __init__(self):
        # Listen on port 5001
        ServerThread.__init__(self, 5001)

        self.alpha_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.beta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.delta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.gamma_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.theta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)

        self.all_contacts_mean = MovingAverage(CONTACT_LOS_TIMEOUT)

        self.state = MuseState()

        self.connections_debug = (0, 0, 0, 0)
        self.lightServerThread = None
        self.startServingLights()

    def kill(self):
        self.lightServerThreadDMX.stop()

    def startServingLights(self):
        self.lightServerThreadDMX = StoppableThread(self.serveDMXLights)
        self.lightServerThreadDMX.start()

    def serveDMXLights(self, thread):
        dmxClient = DMXClient()
        dmxClient.createLightGroup(EEG_LIGHT_GROUP_ADDRESS, Orcan2)
        dmxClient.createLightGroup(SPOTLIGHT_LIGHT_GROUP_ADDRESS, PTVWIRE)
        # Create color mixing
        eegMixer = LightMixer(USER_TO_DEFAULT_FADE_WINDOW, DEFAULT_ANIMATION_RENDER_RATE)
        spotlightMixer = LightMixer(USER_TO_DEFAULT_FADE_WINDOW, DEFAULT_ANIMATION_RENDER_RATE)
        # Start color mixing
        eegMixer.startDefaultColorAnimation()
        spotlightMixer.startDefaultSpotlightAnimation()

        count = LOG_PRINT_RATE / LIGHT_UPDATE_INTERVAL
        while not thread.stopped():
            try:
                eegMixer.updateStateForEEG(self.state)
                spotlightMixer.updateStateForSpotlight(self.state)

                eegColor = eegMixer.getColor()
                spotlightColor = spotlightMixer.getColor()

                # Logging
                if count >= LOG_PRINT_RATE / LIGHT_UPDATE_INTERVAL:
                    e = eegColor
                    s = spotlightColor
                    print "User conectivity: %d raw: %s" % (self.state.connected, str(self.connections_debug))
                    print "Muse data: ALPHA: %f, BETA: %f, DELTA: %f, GAMMA: %f, THETA: %f" % (self.state.alpha, self.state.beta, self.state.delta, self.state.gamma, self.state.theta)
                    print "Muse lights (from Mixer), ADDRESS: %d, COLORS: r: %d g: %d b: %d, BRIGHTNESS: %d" % (EEG_LIGHT_GROUP_ADDRESS, e.r, e.g, e.b, e.brightness)
                    print "Spotlight (from Mixer),   ADDRESS: %d, COLORS: r: %d g: %d b: %d, BRIGHTNESS: %d" % (SPOTLIGHT_LIGHT_GROUP_ADDRESS, s.r, s.g, s.b, s.brightness)
                    count = 0

                dmxClient.updateLightGroup(EEG_LIGHT_GROUP_ADDRESS, eegColor)
                dmxClient.updateLightGroup(SPOTLIGHT_LIGHT_GROUP_ADDRESS, spotlightColor)

                count += 1
                time.sleep(LIGHT_UPDATE_INTERVAL)

            except Exception, err:
                print "Exception in serveDMXLights: ", err.__class__.__name__, err.message
                traceback.print_exc(err)
                dmxClient.kill()
                eegMixer.kill()
                spotlightMixer.kill()
                sys.exit()
        dmxClient.kill()
        eegMixer.kill()
        spotlightMixer.kill()
        sys.exit()

    # receive alpha data

    @make_method('/muse/elements/alpha_relative', 'ffff')
    def alpha_relative_callback(self, path, *args):
        weights = np.array([2, 0, 0, 2])
        values = np.array(args[0])
        alphaWeightedAndNormalized = self.weighter(values, weights, normalizationMin = .1, normalizationMax=.5)
        x = self.alpha_relative_rolling_avg_generator.next(alphaWeightedAndNormalized)
        self.state.alpha = x if not math.isnan(x) else 0

    def weighter(self, values, weights, normalizationMin = 0, normalizationMax = 1):
        avgVal = np.nanmean(np.multiply(values,weights))
        normalizedAvgVal = (avgVal - normalizationMin) / (normalizationMax - normalizationMin)
        return normalizedAvgVal

    # receive beta data
    @make_method('/muse/elements/beta_relative', 'ffff')
    def beta_relative_callback(self, path, *args):
        weights = np.array([0, 2, 0, 2])
        values = args[0]
        betaWeightedAndNormalized = self.weighter(values, weights, normalizationMin=.15, normalizationMax=.7)
        x = self.beta_relative_rolling_avg_generator.next(betaWeightedAndNormalized)
        self.state.beta = x if not math.isnan(x) else 0

    # receive gamma data
    @make_method('/muse/elements/gamma_relative', 'ffff')
    def gamma_relative_callback(self, path, *args):
        values = args[0]
        input_w, input_x, input_y, input_z = values
        x = self.gamma_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
        self.state.gamma = x if not math.isnan(x) else 0

    # receive delta data
    @make_method('/muse/elements/delta_relative', 'ffff')
    def delta_relative_callback(self, path, *args):
        values = args[0]
        input_w, input_x, input_y, input_z = values
        x = self.delta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
        self.state.delta = x if not math.isnan(x) else 0

    # receive theta data
    @make_method('/muse/elements/theta_relative', 'ffff')
    def theta_relative_callback(self, path, *args):
        values = args[0]
        input_w, input_x, input_y, input_z = values
        x = self.theta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
        self.state.theta = x if not math.isnan(x) else 0

    # is good is for whether or not a contact has signal from the brain
    @make_method('/muse/elements/is_good', 'iiii')
    def is_good_callback(self, path, *args):
        values = args[0]
        chan_1, chan_2, chan_3, chan_4 = values
        all_contacts = avg(chan_1, chan_2, chan_3, chan_4)

        # logging
        self.connections_debug = args

        if self.all_contacts_mean.next(all_contacts) == 0 and self.state.connected:
            # It has been at least CONTACT_LOS_TIMEOUT seconds of total LOS on all contacts
            self.state.connected = 0
            print "LOST CONNECTION"

        if all_contacts == 1 and not self.state.connected:
            # This is the first time the user has put the muse on in at least CONTACT_LOS_TIMEOUT second
            print "CONNECTED!!"
            self.state.connected = 1

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

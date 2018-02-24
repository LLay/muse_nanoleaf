from liblo import *
from threading import Thread

import sys
import time
import random
import traceback
import math
import numpy as np

from LightManager import DMXLightManager
from Orcan2 import Orcan2
from PTVWIRE import PTVWIRE
from LightMixer import EEGWaveLightMixer, SpotlightLightMixer
from MovingAverage import MovingAverage, MovingAverageLinear
from StoppableThread import StoppableThread
from HelperClasses import MuseState
import Config as config

# Debugging memory usage
# from guppy import hpy
# h = hpy()

def avg(*values):
    return reduce(lambda x, y: x + y, values) / len(values)

class DMXClient():
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
        self.lightManager.getLightGroup(address).setBrightness(int(color.brightness))

    def updateLightGroupColor(self, address, color):
        self.lightManager.getLightGroup(address).setRGB(int(color.r), int(color.g), int(color.b))

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

        self.alpha_relative_rolling_avg_generator = MovingAverage(config.ROLLING_EEG_WINDOW)
        self.beta_relative_rolling_avg_generator = MovingAverage(config.ROLLING_EEG_WINDOW)
        self.delta_relative_rolling_avg_generator = MovingAverage(config.ROLLING_EEG_WINDOW)
        self.gamma_relative_rolling_avg_generator = MovingAverage(config.ROLLING_EEG_WINDOW)
        self.theta_relative_rolling_avg_generator = MovingAverage(config.ROLLING_EEG_WINDOW)

        self.all_contacts_mean = MovingAverageLinear(config.CONTACT_LOS_TIMEOUT)

        # EEG signals, connected, touching_forehead
        self.state = MuseState()

        self.connections_debug = (0, 0, 0, 0)

        self.lightServerThreadDMX = StoppableThread(self.serveDMXLights)
        self.lightServerThreadDMX.start()
    #
    #     self.state.alpha = .32
    #     self.state.beta = .32
    #     self.state.delta = .32
    #     self.state.gamma = .32
    #     self.state.theta = .32
    #     self.connectThread = StoppableThread(self.connectToggle)
    #     self.connectThread.start()
    #
    # def connectToggle(self, thread):
    #     self.state.connected = 1
    #     self.state.touching_forehead = 1
    #     while not thread.stopped():
    #         self.state.alpha = random.random()
    #         self.state.beta = random.random()
    #         self.state.delta = random.random()
    #         self.state.gamma = random.random()
    #         self.state.theta = random.random()
    #         self.state.connected = abs(1-self.state.connected)
    #         self.state.touching_forehead = abs(1-self.state.touching_forehead)
    #         print( "toggle")
    #         time.sleep(5)
    #     sys.exit()

    def kill(self):
        self.lightServerThreadDMX.stop()
        # self.connectThread.stop()

    def serveDMXLights(self, thread):
        dmxClient = DMXClient()
        dmxClient.createLightGroup(config.EEG_LIGHT_GROUP_ADDRESS, Orcan2)
        dmxClient.createLightGroup(config.SPOTLIGHT_LIGHT_GROUP_ADDRESS, PTVWIRE)
        # Create color mixing
        eegMixer = EEGWaveLightMixer(
            user_to_default_fade_window=config.USER_TO_DEFAULT_FADE_WINDOW,
            default_animation_render_rate=config.DEFAULT_ANIMATION_RENDER_RATE,
            default_animation_brightness=config.DEFAULT_COLOR_ANIMATION_BRIGHTNESS,
            user_light_brightness=config.USER_LIGHT_BRIGHTNESS)
        spotlightMixer = SpotlightLightMixer(
            user_to_default_fade_window=config.USER_TO_DEFAULT_FADE_WINDOW,
            default_animation_render_rate=config.DEFAULT_ANIMATION_RENDER_RATE,
            default_animation_brightness=config.DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS,
            default_animation_brightness_range=config.DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS_RANGE
            )
        # Start color mixing
        eegMixer.startDefaultAnimation()
        spotlightMixer.startDefaultAnimation()

        count = config.LOG_PRINT_RATE / config.LIGHT_UPDATE_INTERVAL
        while not thread.stopped():
            try:
                # print "Updating state: ALPHA: %f, BETA: %f, DELTA: %f, GAMMA: %f, THETA: %f" % (self.state.alpha, self.state.beta, self.state.delta, self.state.gamma, self.state.theta)
                eegMixer.updateState(self.state)
                spotlightMixer.updateState(self.state)

                eegLight = eegMixer.getLight()
                spotlightLight = spotlightMixer.getLight()

                # Logging
                if count >= config.LOG_PRINT_RATE / config.LIGHT_UPDATE_INTERVAL:
                    e = eegLight
                    s = spotlightLight
                    print ""
                    print "User conectivity (binary): %d score: %f raw: %s" % (self.state.connected, self.state.connectionScore, str(self.connections_debug))
                    print "Muse data: ALPHA: %f, BETA: %f, DELTA: %f, GAMMA: %f, THETA: %f" % (self.state.alpha, self.state.beta, self.state.delta, self.state.gamma, self.state.theta)
                    print "Muse lights (from Mixer), ADDRESS: %d, COLORS: r: %d g: %d b: %d, BRIGHTNESS: %d" % (config.EEG_LIGHT_GROUP_ADDRESS, e.r, e.g, e.b, e.brightness)
                    print "Spotlight (from Mixer),   ADDRESS: %d, COLORS: r: %d g: %d b: %d, BRIGHTNESS: %d" % (config.SPOTLIGHT_LIGHT_GROUP_ADDRESS, s.r, s.g, s.b, s.brightness)
                    count = 0

                dmxClient.updateLightGroup(config.EEG_LIGHT_GROUP_ADDRESS, eegLight)
                dmxClient.updateLightGroup(config.SPOTLIGHT_LIGHT_GROUP_ADDRESS, spotlightLight)

                count += 1
                time.sleep(config.LIGHT_UPDATE_INTERVAL)

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
        self.dimLights(dmxClient)
        sys.exit()

    # Dim the light over 2 seconds. Then as a precaution set their colors to black
    def dimLights(self, dmxClient):
        # number of decaseconds to fade
        fadeCount = 200

        currentColorState = MuseState()
        currentSpotlightState = MuseState()
        # These initial values are guessed, TODO actually know the current brightness
        currentColorState.brightness = config.DEFAULT_COLOR_ANIMATION_BRIGHTNESS
        currentSpotlightState.brightness = config.DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS
        for _ in range(fadeCount):
            currentColorState.brightness -= config.DEFAULT_COLOR_ANIMATION_BRIGHTNESS / float(fadeCount)
            currentSpotlightState.brightness -= config.DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS / float(fadeCount)
            currentColorState.brightness = max(0, int(currentColorState.brightness)) # enforce int, no negative
            currentSpotlightState.brightness = max(0, int(currentSpotlightState.brightness)) # enforce int, no negative
            dmxClient.updateLightGroupBrightness(config.EEG_LIGHT_GROUP_ADDRESS, currentColorState)
            dmxClient.updateLightGroupBrightness(config.SPOTLIGHT_LIGHT_GROUP_ADDRESS, currentSpotlightState)
            print "currentColorState.brightness", currentColorState.brightness
            print "currentSpotlightState.brightness", currentSpotlightState.brightness
            time.sleep(0.01)

    # receive alpha data
    @make_method('/muse/elements/alpha_relative', 'ffff')
    def alpha_relative_callback(self, path, *args):
        weights = np.array([2, 0, 0, 2])
        values = np.array(args[0])
        alphaWeightedAndNormalized = self.weighter(values, weights, normalizationMin = .1, normalizationMax=.5)
        x = self.alpha_relative_rolling_avg_generator.next(alphaWeightedAndNormalized)
        self.state.alpha = x if not math.isnan(x) else 0

    # receive beta data
    @make_method('/muse/elements/beta_relative', 'ffff')
    def beta_relative_callback(self, path, *args):
        weights = np.array([0, 2, 2, 0])
        values = args[0]
        betaWeightedAndNormalized = self.weighter(values, weights, normalizationMin=.15, normalizationMax=.6)
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
        # TODO apparently this callback never gets called
        x = int(arg) if not math.isnan(arg[0]) else 0
        self.state.touching_forehead = x

    # horseshoe gives more granular information on which contacts have signal
    # from the brain
    # We get a tuple of 4 numbers, each representing the connectivity of
    # each contact 1 = good, 2 = ok, >=3 bad
    @make_method('/muse/elements/horseshoe', 'ffff')
    def horseshoe_callback(self, path, args):
        # A score between 0 and 1 of how good the connections of the contacts are
        connectionScore = (8 - (sum(map(lambda x: x if x <= 3 else 3, args)) - 4)) / 8.0
        self.state.connectionScore = connectionScore

        if self.all_contacts_mean.next(connectionScore) == 0 and self.state.connected:
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

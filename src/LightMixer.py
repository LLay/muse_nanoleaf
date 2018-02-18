import pytweening
import random
import colorsys
import time
import sys

from HelperClasses import MuseState
from MovingAverage import MovingAverage
from StoppableThread import StoppableThread

class ColorState:
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0
        self.brightness = 0

def ease(easingFunc, old_value, new_value, current_increment, final_increment):
    percentComplete = abs(float(current_increment) / float(final_increment))
    diff = (old_value - new_value)
    increment = diff * easingFunc(percentComplete)
    return old_value - increment

class LightMixer():
    def __init__(self, user_to_default_fade_window, default_animation_render_rate):
        self.connected_rolling_mean_generator = MovingAverage(user_to_default_fade_window)
        self.connected_mean = 0

        self.userState = MuseState()

        self.userColor = ColorState()
        self.defaultColor = ColorState()
        self.mixedColor = ColorState()

        self.default_animation_render_rate = default_animation_render_rate

    def startDefaultColorAnimation(self):
        self.defaultColorThread = StoppableThread(self.serveDefaultColorAnimation, )
        self.defaultColorThread.start()

    def startDefaultSpotlightAnimation(self):
        self.spotlightThread = StoppableThread(self.serveDefaultSpotlightAnimation, )
        self.spotlightThread.start()

    def serveDefaultSpotlightAnimation(self, thread):
        timeToNextColor = 0
        currentTime = 0
        self.defaultColor.r,self.defaultColor.g,self.defaultColor.b = 255,255,255 # Starting color. White
        self.defaultColor.brightness = 75
        while not thread.stopped():
            if currentTime == timeToNextBrightness:
                brightness_old = brightness
                # https://stackoverflow.com/questions/43437309/get-a-bright-random-colour-python
                brightness = random.randint(75,100)
                timeToNextBrightness = random.randint(6/self.default_animation_render_rate,8/self.default_animation_render_rate)
                currentTime = 0

            self.defaultColor.brightness = ease(pytweening.easeInOutQuad, brightness_old, brightness, currentTime, timeToNextBrightness)

            currentTime += 1
            time.sleep(self.default_animation_render_rate)
        sys.exit()


    def serveDefaultColorAnimation(self, thread):
        timeToNextColor = 0
        currentTime = 0
        r,g,b = 0,0,0 # Starting color
        while not thread.stopped():
            if currentTime == timeToNextColor:
                r_old,g_old,b_old = r,g,b
                # https://stackoverflow.com/questions/43437309/get-a-bright-random-colour-python
                h,s,l = random.random(), 0.5 + random.random()/2.0, 0.4 + random.random()/5.0
                r,g,b = [int(256*i) for i in colorsys.hls_to_rgb(h,l,s)]
                timeToNextColor = random.randint(4/self.default_animation_render_rate,6/self.default_animation_render_rate)
                currentTime = 0

            self.defaultColor.r = ease(pytweening.easeInOutQuad, r_old, r, currentTime, timeToNextColor)
            self.defaultColor.g = ease(pytweening.easeInOutQuad, g_old, g, currentTime, timeToNextColor)
            self.defaultColor.b = ease(pytweening.easeInOutQuad, b_old, b, currentTime, timeToNextColor)

            currentTime += 1
            time.sleep(self.default_animation_render_rate)
        sys.exit()

    # This mixes the use and default colours depending on if the user is connected or not
    def updateMixedColor(self):
        self.mixedColor.r = (self.userColor.r * self.connected_mean) + (self.defaultColor.r * (1-self.connected_mean))
        self.mixedColor.g = (self.userColor.g * self.connected_mean) + (self.defaultColor.g * (1-self.connected_mean))
        self.mixedColor.b = (self.userColor.b * self.connected_mean) + (self.defaultColor.b * (1-self.connected_mean))

    # interprets user state as a color
    def updateUserColorEEG(self):
        # Very simple linear mapping, not even of all eeg
        # raw values are between -1 and 1. map it to 0-255
        self.userColor.r = ((self.userState.delta + 1) / 2) * 255
        self.userColor.g = ((self.userState.beta + 1) / 2) * 255
        self.userColor.b = ((self.userState.alpha + 1) / 2) * 255

    # This function can be asynced if need be
    def updateStateForEEG(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        self.updateUserColorEEG()
        self.updateMixedColor()

    # This function can be asynced if need be
    def updateStateForSpotlight(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        # We leave the user colors as black, to fade the spotlight when a user is connected
        self.updateMixedColor()

    def getColor(self):
        return self.mixedColor

    def getColor(self):
        return self.mixedColor

    def kill(self):
        if hasattr(self, 'defaultColorThread'):
            self.defaultColorThread.stop()
        if hasattr(self, 'spotlightThread'):
            self.spotlightThread.stop()

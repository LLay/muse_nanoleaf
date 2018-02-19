import pytweening
import random
import colorsys
import time
import sys

from HelperClasses import MuseState
from MovingAverage import MovingAverage
from StoppableThread import StoppableThread

DEFAULT_COLOR_ANIMATION_BRIGHTNESS = 255

class LightState:
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0
        self.brightness = 0

def ease(easingFunc, old_value, new_value, current_increment, final_increment):
    percentComplete = abs(float(current_increment) / float(final_increment))
    diff = (old_value - new_value)
    increment = diff * easingFunc(percentComplete)
    return int(old_value - increment)

class LightMixer():
    def updateState(self, user_state):
        raise NotImplementedError('Need to implement updateState')
    def getLight(self):
        raise NotImplementedError('Need to implement getLight')
    def kill(self):
        raise NotImplementedError('Need to implement kill')

class SpotlightLightMixer(LightMixer):
    def __init__(self, user_to_default_fade_window, default_animation_render_rate):
        self.default_animation_render_rate = default_animation_render_rate

        # These values help use keep track of when the user is connected to the muse
        self.connected_mean = 0
        self.touching_forehead_mean = 0
        self.connected_rolling_mean_generator = MovingAverage(user_to_default_fade_window)
        self.touching_forehead_mean_generator = MovingAverage(user_to_default_fade_window)

        self.userState = MuseState()

        # The data that represents the muse data
        self.userLight = LightState()
        # The current colour of the default animation
        self.defaultLight = LightState()
        # The weighted mix of the user and default animation color.
        # When the user connects (to the muse) this color will transition
        # over 3 seconds to be their color, whe the user disconnects, this color
        # transitions to the default animation color
        self.mixedLight = LightState()

    def startDefaultAnimation(self):
        self.defaultAnimationThread = StoppableThread(self.serveDefaultAnimation, )
        self.defaultAnimationThread.start()

    def serveDefaultAnimation(self, thread):
        #settings
        brightness_lower_bound = 100
        brightness_upper_bound = 200

        # initialize animation values
        timeToNextBrightness = 0
        currentTime = 0
        self.defaultLight.r,self.defaultLight.g,self.defaultLight.b = 255,255,255 # Starting color. White
        brightness = brightness_lower_bound
        while not thread.stopped():
            if currentTime == timeToNextBrightness:
                brightness_old = brightness
                brightness = random.randint(brightness_lower_bound, brightness_upper_bound)
                timeToNextBrightness = random.randint(6/self.default_animation_render_rate,8/self.default_animation_render_rate)
                currentTime = 0

            self.defaultLight.brightness = ease(pytweening.easeInOutQuad, brightness_old, brightness, currentTime, timeToNextBrightness)

            currentTime += 1
            time.sleep(self.default_animation_render_rate)
        sys.exit()

    # This mixes the use and default colours depending on if the user is connected or not
    def updateMixedLight(self):
        self.mixedLight.r = int((self.userLight.r * self.connected_mean) + (self.defaultLight.r * (1-self.connected_mean)))
        self.mixedLight.g = int((self.userLight.g * self.connected_mean) + (self.defaultLight.g * (1-self.connected_mean)))
        self.mixedLight.b = int((self.userLight.b * self.connected_mean) + (self.defaultLight.b * (1-self.connected_mean)))
        self.mixedLight.brightness = int((self.userLight.brightness * self.connected_mean) + (self.defaultLight.brightness * (1-self.connected_mean)))

    # This function can be asynced if need be
    def updateState(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        self.updateMixedLight()
        # Note that we leave the user colors as black,
        # to fade the spotlight off when a user is connected

    def getLight(self):
        return self.mixedLight

    def kill(self):
        if hasattr(self, 'defaultAnimationThread'):
            self.defaultAnimationThread.stop()


class EEGWaveLightMixer(LightMixer):
    def __init__(self, user_to_default_fade_window, default_animation_render_rate):
        self.default_animation_render_rate = default_animation_render_rate

        # These values help use keep track of when the user is connected to the muse
        self.connected_mean = 0
        self.touching_forehead_mean = 0
        self.connected_rolling_mean_generator = MovingAverage(user_to_default_fade_window)
        self.touching_forehead_mean_generator = MovingAverage(user_to_default_fade_window)

        self.userState = MuseState()

        # The data that represents the muse data
        self.userLight = LightState()
        # The current colour of the default animation
        self.defaultLight = LightState()
        # The weighted mix of the user and default animation color.
        # When the user connects (to the muse) this color will transition
        # over 3 seconds to be their color, whe the user disconnects, this color
        # transitions to the default animation color
        self.mixedLight = LightState()

    def startDefaultAnimation(self):
        self.defaultAnimationThread = StoppableThread(self.serveDefaultAnimation, )
        self.defaultAnimationThread.start()

    def serveDefaultAnimation(self, thread):
        timeToNextColor = 0
        currentTime = 0
        r,g,b = 0,0,0 # Starting color

        # TODO move to Env var
        self.defaultLight.brightness = DEFAULT_COLOR_ANIMATION_BRIGHTNESS

        while not thread.stopped():
            if currentTime == timeToNextColor:
                r_old,g_old,b_old = r,g,b
                # https://stackoverflow.com/questions/43437309/get-a-bright-random-colour-python
                h,s,l = random.random(), 0.5 + random.random()/2.0, 0.4 + random.random()/5.0
                r,g,b = [int(256*i) for i in colorsys.hls_to_rgb(h,l,s)]
                timeToNextColor = random.randint(4/self.default_animation_render_rate,6/self.default_animation_render_rate)
                currentTime = 0

            self.defaultLight.r = ease(pytweening.easeInOutQuad, r_old, r, currentTime, timeToNextColor)
            self.defaultLight.g = ease(pytweening.easeInOutQuad, g_old, g, currentTime, timeToNextColor)
            self.defaultLight.b = ease(pytweening.easeInOutQuad, b_old, b, currentTime, timeToNextColor)

            # Dim the animation when the user puts on the muse
            # Dim to a minimum of 20% of the original animation brightness
            brightnessModifier = 1-self.touching_forehead_mean if 1-self.touching_forehead_mean >= 0.2 else 0.2
            self.defaultLight.brightness = DEFAULT_COLOR_ANIMATION_BRIGHTNESS * (1-self.touching_forehead_mean)

            currentTime += 1
            time.sleep(self.default_animation_render_rate)
        sys.exit()

    # This mixes the use and default colours depending on if the user is connected or not
    def updateMixedLight(self):
        self.mixedLight.r = int((self.userLight.r * self.connected_mean) + (self.defaultLight.r * (1-self.connected_mean)))
        self.mixedLight.g = int((self.userLight.g * self.connected_mean) + (self.defaultLight.g * (1-self.connected_mean)))
        self.mixedLight.b = int((self.userLight.b * self.connected_mean) + (self.defaultLight.b * (1-self.connected_mean)))
        self.mixedLight.brightness = int((self.userLight.brightness * self.connected_mean) + (self.defaultLight.brightness * (1-self.connected_mean)))

    # interprets user state as a color
    def updateUserColorEEG(self):
        # Very simple linear mapping, not even of all eeg
        # raw values are between -1 and 1. map it to 0-255
        #
        self.userLight.r = ((self.userState.delta + 1) / 2.0) * 255
        self.userLight.g = ((self.userState.beta + 1) / 2.0) * 255
        self.userLight.b = ((self.userState.alpha + 1) / 2.0) * 255
        self.userLight.brightness = 125

    # This function can be asynced if need be
    def updateState(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        self.touching_forehead_mean = self.touching_forehead_mean_generator.next(user_state.touching_forehead)
        self.updateUserColorEEG()
        self.updateMixedLight()

    def getLight(self):
        return self.mixedLight

    def kill(self):
        if hasattr(self, 'defaultAnimationThread'):
            self.defaultAnimationThread.stop()

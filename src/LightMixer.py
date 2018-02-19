import pytweening
import random
import colorsys
import time
import sys

from HelperClasses import MuseState
from MovingAverage import MovingAverage
from StoppableThread import StoppableThread

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
    def __init__(self,
        user_to_default_fade_window,
        default_animation_render_rate,
        default_animation_brightness,
        default_animation_brightness_range):
        self.default_animation_render_rate = default_animation_render_rate
        self.default_animation_brightness = default_animation_brightness
        self.default_animation_brightness_range = default_animation_brightness_range

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
        # over 3 seconds to be their color, when the user disconnects, this color
        # transitions to the default animation color
        self.mixedLight = LightState()

    def startDefaultAnimation(self):
        self.defaultAnimationThread = StoppableThread(self.serveDefaultAnimation, )
        self.defaultAnimationThread.start()

    def serveDefaultAnimation(self, thread):
        # Undulation bounds
        brightness_lower_bound = self.default_animation_brightness - (self.default_animation_brightness_range / 2)
        brightness_lower_bound = max(0, brightness_lower_bound)

        brightness_upper_bound = self.default_animation_brightness + (self.default_animation_brightness_range / 2)
        brightness_upper_bound = min(255, brightness_upper_bound)

        # initialize animation values
        timeToNextBrightness = 0
        currentTime = 0
        self.defaultLight.r,self.defaultLight.g,self.defaultLight.b = 255,255,255 # Starting color. White
        brightness = 0
        while not thread.stopped():
            if currentTime == timeToNextBrightness:
                brightness_old = brightness
                brightness = random.randint(brightness_lower_bound, brightness_upper_bound)
                timeToNextBrightness = random.randint(6/self.default_animation_render_rate,8/self.default_animation_render_rate)
                currentTime = 0

            undulatingBrightness = ease(pytweening.easeInOutQuad, brightness_old, brightness, currentTime, timeToNextBrightness)
            self.defaultLight.brightness = undulatingBrightness * (1-self.userState.connectionScore)

            currentTime += 1
            time.sleep(self.default_animation_render_rate)
        sys.exit()

    # This mixes the use and default colours depending on if the user is connected or not
    def updateMixedLight(self):
        self.mixedLight.r = int((self.userLight.r * self.connected_mean) + (self.defaultLight.r * (1-self.connected_mean)))
        self.mixedLight.g = int((self.userLight.g * self.connected_mean) + (self.defaultLight.g * (1-self.connected_mean)))
        self.mixedLight.b = int((self.userLight.b * self.connected_mean) + (self.defaultLight.b * (1-self.connected_mean)))
        self.mixedLight.brightness = int((self.userLight.brightness * self.connected_mean) + (self.defaultLight.brightness * (1-self.connected_mean)))

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
    def __init__(self,
        user_to_default_fade_window,
        default_animation_render_rate,
        default_animation_brightness,
        user_light_brightness):
        self.default_animation_render_rate = default_animation_render_rate
        self.default_animation_brightness = default_animation_brightness
        self.user_light_brightness = user_light_brightness

        # These values help use keep track of when the user is connected to the muse
        self.connected_mean = 0
        self.touching_forehead_mean = 0
        self.connected_rolling_mean_generator = MovingAverage(user_to_default_fade_window)
        self.touching_forehead_mean_generator = MovingAverage(user_to_default_fade_window)

        # Muse data, and user info
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
        r,g,b = 0,0,0 # Starting color. Black

        self.defaultLight.brightness = self.default_animation_brightness

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
            # TODO
            brightnessModifier = 1-self.touching_forehead_mean
            brightnessModifier = max(0.2, brightnessModifier)
            self.defaultLight.brightness = self.default_animation_brightness * (1-self.touching_forehead_mean)

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
    def updateUserLight(self):
        # raw values are between 0 and 1. map it to 0-255
        self.userLight.r = self.userState.delta * 255
        self.userLight.g = self.userState.beta * 255
        self.userLight.b = self.userState.alpha * 255
        self.userLight.brightness = self.user_light_brightness

    # This function can be asynced if need be
    def updateState(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        self.touching_forehead_mean = self.touching_forehead_mean_generator.next(user_state.touching_forehead)
        self.updateUserLight()
        self.updateMixedLight()

    def getLight(self):
        return self.mixedLight

    def kill(self):
        if hasattr(self, 'defaultAnimationThread'):
            self.defaultAnimationThread.stop()

from liblo import *
from collections import deque

import sys
import time
import threading
import random
import colorsys
import pytweening

from LightManager import Orcan2LightManager

from guppy import hpy
h = hpy()

import urllib2

# How often we update the lights. Measured in seconds. Minimum of 0.1 (You can go lower, but we only get data from the muse at 10Hz)
LIGHT_UPDATE_INTERVAL = 0.1
# How often when render an new frame of the default animation
DEFAULT_ANIMATION_RENDER_RATE = 0.1
# Number of second over which we average eeg signals.
ROLLING_EEG_WINDOW = 3
# Number of second over which fade between user input and the default light animation.
USER_TO_DEFAULT_FADE_WINDOW = 5
# The delay in seconds between loss of signal on all contacts and ..doing something about it
CONTACT_LOS_TIMEOUT = 3

# Correct decimal place for relevant values. Don't change me!
ROLLING_EEG_WINDOW *= 10
CONTACT_LOS_TIMEOUT *= 10

# https://github.com/kamyu104/LeetCode/blob/master/Python/moving-average-from-data-stream.py
# Not weighted
class MovingAverage(object):

    def __init__(self, size):
        """
        Initialize your data structure here.
        :type size: int
        """
        self.__size = size
        self.__sum = 0
        self.__q = deque([])

    def next(self, val):
        """
        :type val: int
        :rtype: float
        """
        if len(self.__q) == self.__size:
            self.__sum -= self.__q.popleft()
        self.__sum += val
        self.__q.append(val)
        return 1.0 * self.__sum / len(self.__q)

def avg(*values):
    return reduce(lambda x, y: x + y, values) / len(values)

# # @t is the current time (or position) of the tween. This can be seconds or frames, steps, seconds, ms, whatever - as long as the unit is the same as is used for the total time [3].
# # @b is the beginning value of the property.
# # @c is the change between the beginning and destination value of the property.
# # @d is the total time of the tween.
# def easeInOutQuad(t, b, c, d):
# 	t /= d/2
# 	if t < 1:
# 		return c/2*t*t + b
# 	t-=1
# 	return -c/2 * (t*(t-2) - 1) + b

def getIncrement(old_value, new_value, current_increment, final_increment):
    percentComplete = abs(float(current_increment) / float(final_increment))
    # print "current_increment", current_increment, "/ final_increment", final_increment, "percentComplete", percentComplete
    diff = (old_value - new_value)
    increment = diff * pytweening.easeInOutQuad(percentComplete)
    # print "increment", increment, "diff", diff, "percentComplete",percentComplete,  "old_value", old_value, "new_value", new_value, "final_increment", final_increment, "current_increment", current_increment
    return old_value - increment

class LightMixer():
    def __init__(self):
        self.connected_rolling_mean_generator = MovingAverage(USER_TO_DEFAULT_FADE_WINDOW)
        self.connected_mean = 0

        self.userState = MuseState()

        self.userColor = ColorState()
        self.defaultColor = ColorState()
        self.mixedColor = ColorState()

        self.startDefaultColorAnimation()

    def startDefaultColorAnimation(self):
        self.defaultColorThread = StoppableThread(self.serveDefaultColorAnimation, )
        self.defaultColorThread.start()

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
                timeToNextColor = random.randint(4/DEFAULT_ANIMATION_RENDER_RATE,6/DEFAULT_ANIMATION_RENDER_RATE)
                currentTime = 0

            thing = getIncrement(r_old, r, currentTime, timeToNextColor)
            self.defaultColor.r = thing
            self.defaultColor.g = getIncrement(g_old, g, currentTime, timeToNextColor)
            self.defaultColor.b = getIncrement(b_old, b, currentTime, timeToNextColor)

            # print "#### time:",currentTime, timeToNextColor, "Red range: ", r_old, r, "Red Val: ", self.defaultColor.r, thing
            currentTime += 1
            time.sleep(DEFAULT_ANIMATION_RENDER_RATE)
    #
    # def serveDefaultColorAnimation(self, thread):
    #
    #     timeToNextColor = 0
    #     currentTime = 0
    #     r,g,b = 0,0,0 # Starting color
    #     while not thread.stopped():
    #         if currentTime == timeToNextColor:
    #             r_old,g_old,b_old = r,g,b
    #             # https://stackoverflow.com/questions/43437309/get-a-bright-random-colour-python
    #             h,s,l = random.random(), 0.5 + random.random()/2.0, 0.4 + random.random()/5.0
    #             r,g,b = [int(256*i) for i in colorsys.hls_to_rgb(h,l,s)]
    #             timeToNextColor = random.randint(4/DEFAULT_ANIMATION_RENDER_RATE,6/DEFAULT_ANIMATION_RENDER_RATE)
    #             currentTime = 0
    #
    #         self.defaultColor.r = easeInOutQuad(currentTime, r_old, abs(r - r_old), timeToNextColor)
    #         self.defaultColor.g = easeInOutQuad(currentTime, g_old, abs(g - g_old), timeToNextColor)
    #         self.defaultColor.b = easeInOutQuad(currentTime, b_old, abs(b - b_old), timeToNextColor)
    #
    #         print currentTime, r_old, abs(r - r_old), timeToNextColor, "RGB: ", self.defaultColor.r,self.defaultColor.g,self.defaultColor.b
    #         currentTime += 1
    #         time.sleep(DEFAULT_ANIMATION_RENDER_RATE)

    # This mixes the use and default colours depending on if the user is connected or not
    def updateMixedColor(self):
        self.mixedColor.r = (self.userColor.r * self.connected_mean) + (self.defaultColor.r * (1-self.connected_mean))
        self.mixedColor.g = (self.userColor.g * self.connected_mean) + (self.defaultColor.g * (1-self.connected_mean))
        self.mixedColor.b = (self.userColor.b * self.connected_mean) + (self.defaultColor.b * (1-self.connected_mean))

    # interprets user state as a color
    def updateUserColor(self):
        # Very simple linear mapping, not even of all eeg
        # raw values are between -1 and 1. map it to 0-255
        self.userColor.r = ((self.userState.delta + 1) / 2) * 255
        self.userColor.g = ((self.userState.beta + 1) / 2) * 255
        self.userColor.b = ((self.userState.alpha + 1) / 2) * 255

    def updateState(self, user_state):
        self.userState = user_state
        self.connected_mean = self.connected_rolling_mean_generator.next(user_state.connected)
        self.updateUserColor()

    def getColor(self):
        self.updateMixedColor()
        return self.mixedColor

    def kill(self):
        self.defaultColorThread.stop()


class DMXClient():
    def __init__(self):
        self.mixer = LightMixer()
        self.lightManager = Orcan2LightManager(tickInterval=.01)
        thread = StoppableThread(target = self.lightManager.run)
        thread.start()

    def updateLights(self, new_user_state):

        # print "DMX: %f, %f, %f, %f, %f" % (state.alpha, state.beta, state.delta, state.gamma, state.theta)
        try:
            self.mixer.updateState(new_user_state)
            colorToSendToLights = self.mixer.getColor()
            print colorToSendToLights.r,",", colorToSendToLights.g, ",",colorToSendToLights.b
            self.lightManager.light.setRGB(int(colorToSendToLights.r), int(colorToSendToLights.g), int(colorToSendToLights.b))
        except Exception, err:
            print str(err)
            sys.exit()
        # TODO This is the exit point. Call Eli's light api from here

    def kill(self):
        self.mixer.kill()
        self.lightManager.thread.stop()
        #TODO Implement self.lightManager.kill()

class NodeLeafClient():
    def __init__(self):
        self.mixer = LightMixer()

    def updateLights(self, new_user_state):
        print "NodeLeaf: %f, %f, %f, %f, %f" % (state.alpha, state.beta, state.delta, state.gamma, state.theta)
        colorToSendToLights = self.mixer.getColor()
        # TODO

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target):
        super(StoppableThread, self).__init__(target=target, args=(self,))
        self.target = target
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        # print "stoppped?", self.target
        return self._stop_event.is_set()

class ColorState:
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0

class MuseState():
    def __init__(self):
        self.alpha = 0
        self.beta = 0
        self.delta = 0
        self.gamma = 0
        self.theta = 0
        self.connected = False

# MuseServer
class MuseServer(ServerThread):
    #listen for messages on port 5000
    def __init__(self):
        ServerThread.__init__(self, 5001)

        self.alpha_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.beta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.delta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.gamma_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)
        self.theta_relative_rolling_avg_generator = MovingAverage(ROLLING_EEG_WINDOW)

        self.all_contacts_mean = MovingAverage(CONTACT_LOS_TIMEOUT)

        self.state = MuseState()

        self.lightServerThread = None
        self.startServingLights()

    def kill(self):
        self.lightServerThreadDMX.stop()
        self.lightServerThreadNanoLeaf.stop()
        self.debug = False

    def startServingLights(self):
        self.lightServerThreadDMX = StoppableThread(self.serveDMXLights)
        self.lightServerThreadNanoLeaf = StoppableThread(self.serveNanoLeafLights)

        self.lightServerThreadDMX.start()
        # self.lightServerThreadNanoLeaf.start()

    def serveDMXLights(self, thread):
        client = DMXClient()
        while not thread.stopped():
            try:
                client.updateLights(self.state)
                time.sleep(LIGHT_UPDATE_INTERVAL)
            except:
                client.kill()
        client.kill()

    def serveNanoLeafLights(self, thread):
        client = NodeLeafClient()


    # receive delta data
    @make_method('/muse/elements/delta_relative', 'ffff')
    def delta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.state.delta = self.delta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive theta data
    @make_method('/muse/elements/theta_relative', 'ffff')
    def theta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.state.theta = self.theta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive alpha data
    @make_method('/muse/elements/alpha_relative', 'ffff')
    def alpha_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.state.alpha = self.alpha_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive beta data
    @make_method('/muse/elements/beta_relative', 'ffff')
    def beta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.state.beta = self.beta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive gamma data
    @make_method('/muse/elements/gamma_relative', 'ffff')
    def gamma_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.state.gamma = self.gamma_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))


    # is good is for whether or not a contact has signal from the brain
    @make_method('/muse/elements/is_good', 'iiii')
    def is_good_callback(self, path, args):
        chan_1, chan_2, chan_3, chan_4 = args
        all_contacts = avg(chan_1, chan_2, chan_3, chan_4)
        # print "%s, %f, %f, %f, %f" % (path, chan_1, chan_2, chan_3, chan_4)

        if self.all_contacts_mean.next(all_contacts) == 0 and self.state.connected:
            # It has been at least CONTACT_LOS_TIMEOUT seconds of total LOS on all contacts
            self.state.connected = 0

        if all_contacts == 1 and not self.state.connected:
            # This is the first time the user has put the muse on in at least CONTACT_LOS_TIMEOUT second
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


# FAILED profiling attempts
# cProfile.run('server.start()')
# prof = prof.runctx("server.start()", globals(), locals())
#
# import cProfile, pstats
# prof = cProfile.Profile()
# prof = prof.runctx("server.start()", globals(), locals())
#
# while 1:
#     time.sleep(1)
#     stats = pstats.Stats(prof)
#     stats.sort_stats("time")  # Or cumulative
#     stats.print_stats(80)  # 80 = how many to print


if __name__ == "__main__":
    while 1:
        try:
            time.sleep(1)
            server
        except KeyboardInterrupt:
            server.kill()
            sys.exit()

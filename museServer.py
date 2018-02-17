from liblo import *
from collections import deque

import sys
import time
import threading

from guppy import hpy
h = hpy()

# Number of second over which we average eeg signals.
ROLLING_MEAN_WINDOW = 3
# The delay in seconds between loss of signal on all contacts and ..doing something about it
CONTACT_LOS_TIMEOUT = 3
# How often we update the lights. Measured in seconds
LIGHT_UPDATE_INTERVAL = 0.1

# Correct decimal place for relevant values. Don't change me!
ROLLING_MEAN_WINDOW *= 10
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


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target):
        super(StoppableThread, self).__init__(target=target, args=(self,))
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

# MuseServer
class MuseServer(ServerThread):
    #listen for messages on port 5000
    def __init__(self):
        ServerThread.__init__(self, 5001)
        # Testing
        self.relative_alpha_mean = MovingAverage(ROLLING_MEAN_WINDOW)

        self.delta_relative_rolling_avg_generator = MovingAverage(ROLLING_MEAN_WINDOW)
        self.theta_relative_rolling_avg_generator = MovingAverage(ROLLING_MEAN_WINDOW)
        self.alpha_relative_rolling_avg_generator = MovingAverage(ROLLING_MEAN_WINDOW)
        self.beta_relative_rolling_avg_generator = MovingAverage(ROLLING_MEAN_WINDOW)
        self.gamma_relative_rolling_avg_generator = MovingAverage(ROLLING_MEAN_WINDOW)

        self.delta = 0
        self.theta = 0
        self.alpha = 0
        self.beta = 0
        self.gamma = 0

        self.all_contacts_mean = MovingAverage(CONTACT_LOS_TIMEOUT)
        self.connected = False

        self.lightServerThread = None
        self.startServingLights()

    def kill(self):
        self.lightServerThread.stop()
        self.debug = False

    def startServingLights(self):
        self.lightServerThread = StoppableThread(self.serveLights)
        # t = threading.Thread(target=self.serveLights)
        self.lightServerThread.start()

    def serveLights(self, thread):
        while not thread.stopped():
            self.sendStateToDMX()
            time.sleep(LIGHT_UPDATE_INTERVAL)

    # use all of the self.x_relative_value values to mix a signal to the lights
    def sendStateToDMX(self):
        print "sending state: %f, %f, %f, %f, %f" % (
            self.delta,
            self.theta,
            self.alpha,
            self.beta,
            self.gamma)


    # receive alpha data
    # @make_method('/muse/elements/alpha_absolute', 'ffff')
    # def alpha_relative_callback(self, path, args):
    #     alpha_w, alpha_x, alpha_y, alpha_z = args
    #     print "%f, %f, %f, %f" % ( alpha_w, alpha_x, alpha_y, alpha_z)
        # print "%f, %f, %f, %f" % ( alpha_w, alpha_z, avg(alpha_w, alpha_z), self.relative_alpha_mean.next(avg(alpha_w, alpha_z)))
        # print "%s, %f, %f, %f, %f" % (path, alpha_w, alpha_x, alpha_y, alpha_z)
        # print "%s, %f, %f" % (path, alpha_w, self.relative_alpha_mean.next(alpha_w))
        # print h.heap

    # receive delta data
    @make_method('/muse/elements/delta_relative', 'ffff')
    def delta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.delta = self.delta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive theta data
    @make_method('/muse/elements/theta_relative', 'ffff')
    def theta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.theta = self.theta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive alpha data
    @make_method('/muse/elements/alpha_relative', 'ffff')
    def alpha_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.alpha = self.alpha_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive beta data
    @make_method('/muse/elements/beta_relative', 'ffff')
    def beta_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.beta = self.beta_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))
    # receive gamma data
    @make_method('/muse/elements/gamma_relative', 'ffff')
    def gamma_relative_callback(self, path, args):
        input_w, input_x, input_y, input_z = args
        self.gamma = self.gamma_relative_rolling_avg_generator.next(avg(input_w, input_x, input_y, input_z))


    # is good is for whether or not a contact has signal from the brain
    @make_method('/muse/elements/is_good', 'iiii')
    def is_good_callback(self, path, args):
        chan_1, chan_2, chan_3, chan_4 = args
        # print "%s, %f, %f, %f, %f" % (path, chan_1, chan_2, chan_3, chan_4)

        all_contacts = avg(chan_1, chan_2, chan_3, chan_4)

        if self.all_contacts_mean.next(all_contacts) == 0 and self.connected:
            # It has been at least CONTACT_LOS_TIMEOUT seconds of total LOS on all contacts
            self.connected = False
            # TODO trigger something to set default light animation

        if all_contacts == 1 and not self.connected:
            # This is the first time the user has put the muse on in at least CONTACT_LOS_TIMEOUT second
            self.connected = True
            # TODO trigger the lights to sync with muse input

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

from collections import deque
import math

class MovingAverageExponential(object):
    def __init__(self, size):
        """
        Initialize your data structure here.
        :type size: int
        """
        self.__size = size if size >= 1 else 1
        self.__sum = 0
        self.__q = deque([])
        self.__exponential_backoff = .97
    def next(self, val, printDebug = False):
        """
        :type val: int
        :rtype: float
        """
        val = val if not math.isnan(val) else 0
        if len(self.__q) >= self.__size:
            subVal = self.__q.popleft()
            self.__sum -= self.__exponential_backoff**(len(self.__q)-1)*subVal
        self.__sum = (self.__sum*self.__exponential_backoff) + val
        self.__q.append(val)
        return max(min(1.0 * self.__sum / self.computeBackoffMass(len(self.__q)),1),0)

    def computeBackoffMass(self, n):
        return self.__exponential_backoff*(1-self.__exponential_backoff**(n))/(1-self.__exponential_backoff)

# https://github.com/kamyu104/LeetCode/blob/master/Python/moving-average-from-data-stream.py
# Not weighted
class MovingAverageLinear(object):
    def __init__(self, size):
        """
        Initialize your data structure here.
        :type size: int
        """
        self.__size = size
        self.__sum = 0
        self.__q = deque([])

    def next(self, val, printDebug = False):
        """
        :type val: int
        :rtype: float
        """
        if len(self.__q) == self.__size:
            self.__sum -= self.__q.popleft()
        self.__sum += val
        self.__q.append(val)
        return 1.0 * self.__sum / len(self.__q)

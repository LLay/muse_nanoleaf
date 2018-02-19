from collections import deque
import math

# https://github.com/kamyu104/LeetCode/blob/master/Python/moving-average-from-data-stream.py
# Not weighted
class MovingAverage(object):

    def __init__(self, size):
        """
        Initialize your data structure here.
        :type size: int
        """
        self.__size = size if size >= 1 else 1
        self.__sum = 0
        self.__q = deque([])

    def next(self, val):
        """
        :type val: int
        :rtype: float
        """
        val = val if not math.isnan(val) else 0
        if len(self.__q) == self.__size:
            self.__sum -= self.__q.popleft()
        self.__sum += val
        self.__q.append(val)
        return 1.0 * self.__sum / len(self.__q)

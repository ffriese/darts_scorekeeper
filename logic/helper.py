import time
from collections import OrderedDict

import numpy as np


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class TimerObject(object):
    def __init__(self):
        self.start = time.time()
        self.segments = OrderedDict()

    def finished(self, label):
        t = time.time()
        self.segments[label] = t

    def get_report(self):
        last = self.start
        for label in self.segments.keys():
            print('%s took %f s' % (label, self.segments[label]-last))
            last = self.segments[label]
        print('total: %f s' % (list(self.segments.values())[-1]-self.start))


class MathHelper:
    ONE_THIRD = 1.0 / 3.0
    TWO_THIRD = 2.0 / 3.0
    ONE_SIXTH = 1.0 / 6.0

    @staticmethod
    def vectorized_hsl_to_rgb(h):
        def _v(x):
            x %= 1.0
            c1 = x < MathHelper.TWO_THIRD
            c2 = x < 0.5
            c3 = x < MathHelper.ONE_SIXTH
            res = np.zeros(x.shape)
            res[c1] = (MathHelper.TWO_THIRD - x[c1]) * 6.0
            res[c2] = 1.0
            res[c3] = x[c3] * 6.0
            return res

        return _v(h + MathHelper.ONE_THIRD), _v(h), _v(h - MathHelper.ONE_THIRD)


    @staticmethod
    def vectorized_hsl_to_rgb2(h):
        def _v(x):
            x %= 1.0
            c1 = np.logical_and(x >= 0.5, x < MathHelper.TWO_THIRD)
            c2 = np.logical_and(x >= MathHelper.ONE_SIXTH, x < 0.5)
            c3 = x < MathHelper.ONE_SIXTH
            res = np.zeros(x.shape)
            res[c1] = (MathHelper.TWO_THIRD - x[c1]) * 6.0
            res[c2] = 1.0
            res[c3] = x[c3] * 6.0
            return res

        return _v(h + MathHelper.ONE_THIRD), _v(h), _v(h - MathHelper.ONE_THIRD)
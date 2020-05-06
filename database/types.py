import enum
import json
from typing import List

from PyQt5.QtCore import QPointF
from sqlalchemy import String

from models.dartboard import Segment, Bed


class SQLPointF(String):

    @property
    def python_type(self):
        return QPointF

    def bind_processor(self, dialect):
        def process(value: QPointF):
            if value is None or value.isNull():
                return None
            return '%s,%s' % (value.x(), value.y())

        return process

    def result_processor(self, dialect, col_type):
        def process(value: str):
            try:
                return QPointF(*[float(c) for c in value.split(',')])
            except AttributeError:
                return QPointF()
            except Exception as e:
                print(e)
                return QPointF()
        return process


class SQLSegment(String):

    @property
    def python_type(self):
        return Segment

    def bind_processor(self, dialect):
        def process(value: Segment):
            if value is None:
                return None
            return json.dumps(value.to_json())

        return process

    def result_processor(self, dialect, col_type):
        def process(value: str):
            try:
                return Segment.from_json(json.loads(value))
            except AttributeError:
                return None
            except Exception as e:
                print(e)
                return None
        return process


class IntList(String):

    @property
    def python_type(self):
        return list

    def bind_processor(self, dialect):
        def process(value: List[int]):
            if value is None:
                return None
            return ','.join([str(v) for v in value])

        return process

    def result_processor(self, dialect, col_type):
        def process(value: str):
            try:
                return [int(v) for v in value.split(',')]
            except AttributeError:
                return None
            except Exception as e:
                print(e)
                return None

        return process


class StringEnum(enum.Enum):
    @classmethod
    def from_str(cls, val: str):
        return cls[val]

    def __str__(self):
        return self.name


class DartIntent(StringEnum):
    SCORE = 'SCORE'
    SETUP = 'SETUP'
    CHECKOUT = 'CHECKOUT'


class GameStatus(enum.Enum):
    UNINITIALIZED = -1
    WAITING_FOR_USER_INPUT = 0
    IN_PROGRESS = 1
    LEG_FINISHED = 2
    FINISHED = 3
    BLOCKING = 4


class GameVariant(object):
    pass


class TakeResult(StringEnum):
    WIN = 'WIN'
    BUST = 'BUST'
    UNFINISHED = 'UNFINISHED'
    FINISHED = 'FINISHED'
    CHECK_IN = 'CHECK_IN'

from PyQt5.QtCore import QObject, pyqtSignal

from sqlalchemy import Column, Integer, Sequence


class InvalidDartError(Exception):
    pass


def create_id_column(object_name):
    return Column(Integer, Sequence('%s_id_seq' % object_name), primary_key=True)


class SignalWrapper(object):
    """
    wrapper class to use for non QObjects
    """

    def create_wrapper(self, *args):
        class Wrapper(QObject):
            signal = pyqtSignal(*args)

            def __init__(self):
                super().__init__()

        return Wrapper

    def __init__(self, *args):
        self.wrapped = self.create_wrapper(*args)()

    def connect(self, slot):
        self.wrapped.signal.connect(slot)

    def disconnect(self, slot):
        self.wrapped.signal.disconnect(slot)

    def emit(self, *args, **kwargs):
        self.wrapped.signal.emit(*args, **kwargs)


class Option(object):
    def __init__(self, name: str, type: type, options: list = None, default=None):
        self.name = name
        self.type = type
        self.options = options
        self.default = default



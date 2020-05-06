class SmartSetting(object):
    def __init__(self, value):
        self._value = value
        self._handlers = {}

    def register_change_handler(self, handler, *args, pass_value=True):
        self._handlers[handler] = {'pass_value': pass_value, 'args': args}

    def set(self, v):
        self._value = v
        for handler in self._handlers.keys():
            # print('calling', handler, self._handlers[handler])
            if self._handlers[handler]['pass_value']:
                handler(v, *self._handlers[handler]['args'])
            else:
                handler(*self._handlers[handler]['args'])
        # print('####################')

    def get(self):
        return self._value


class Settings(object):
    SOUND_ENABLED = SmartSetting(False)
    DISPLAY_DARTS = SmartSetting(True)
    DRAG_DARTS_ENABLED = SmartSetting(False)

import json
from enum import Enum

from PyQt5.QtCore import QObject, QPointF, pyqtSignal
from paho.mqtt.client import Client, MQTTMessage

from models.objects.dart import Dart


class BoardState(Enum):
    REMOVE_DARTS = 0
    TAKE_ACTIVE = 1


class MQTTClient(QObject):

    new_mqtt_status = pyqtSignal(dict)
    new_mqtt_dart = pyqtSignal(QPointF)

    def __init__(self, host: str, port: int = 1883):
        super().__init__()
        self.host = host
        self.port = port
        self.client = Client()
        self.status = {
            'connected': False,
            'host': host,
            'port': port
        }

    def setup(self):
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.connect_async(self.host, self.port, 60)
        self.client.message_callback_add('board_coordinate', self.mqtt_dart_received)
        self.client.loop_start()

    def send_board_state(self, state: BoardState):
        if self.status['connected']:
            self.client.publish('board_state', state.name)

    def mqtt_dart_received(self, _, __, msg: MQTTMessage):
        coordinate = json.loads(msg.payload.decode())
        location=QPointF(coordinate['x'], coordinate['y'])
        print('GOT MQTT DART:', location)
        self.new_mqtt_dart.emit(location)

    def update_status(self, connected: bool):
        self.status['connected'] = connected
        print('mqtt status: %s' % self.status)
        self.new_mqtt_status.emit(self.status)

    def on_connect(self, *_):
        self.update_status(True)
        self.client.subscribe('board_coordinate')

    def on_disconnect(self, *_):
        self.update_status(False)


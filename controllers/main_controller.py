from typing import Union

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QPointF

from controllers.database_controller import DatabaseController
from controllers.sound_controller import SoundController
from network.mqtt_client import MQTTClient, BoardState
from models.dartboard import DartBoard
from models.objects.dart import Dart
from models.objects.player import Player
from models.objects.game import Game
from widgets.dialogs import GameCreationDialog


class MainController(QObject):
    # internal -> send update over MQTT
    update_board_state = pyqtSignal(BoardState)
    # STATUS OF MQTT CONNECTION
    update_mqtt_status = pyqtSignal(dict)

    # Darts changed -> visual
    update_take = pyqtSignal(object)

    # game changed
    game_updated = pyqtSignal(Game, bool)   # game object, new game

    # request dialogs
    request_game_choice = pyqtSignal(str, list, object)
    request_multi_select = pyqtSignal(str, list, object, dict)

    def __init__(self):
        super().__init__()
        self.mqtt = MQTTClient(host="dartserver")
        self.game = None

    def initialize(self):
        self.mqtt.new_mqtt_dart.connect(self.process_clicked_dart)
        self.mqtt.new_mqtt_status.connect(self.update_mqtt_status)
        self.update_board_state.connect(self.mqtt.send_board_state)
        self.mqtt.setup()
        unfinished_games = DatabaseController.get_unfinished_games()
        if unfinished_games:
            self.request_game_choice.emit('Continue Game?',
                                          unfinished_games, self.load_game)

    def select_game_to_load(self):
        #games = DatabaseController.get_unfinished_games()
        games = DatabaseController.get_games()
        if games:
            self.request_game_choice.emit('Load Game',
                                          games, self.load_game)

    @pyqtSlot()
    def generate_dart(self):
        if self.game is None:
            return
        if self.game.is_blocked():
            # print('controller ignores darts for blocked games....')
            return
        if not self.game.is_initialized:
            # print('controller ignores darts for uninitialized games....')
            return
        if self.game.winner is not None:
            # print('controller ignores darts for finished games....')
            return
        dart = self.game.generate_next_dart()
        if dart is not None:
            self.process_dart(dart)

    def propagate_current_state(self):
        # FOR DISPLAYING
        cur_take = self.game.get_current_player().get_current_take()
        print('PROPAGATE. CURTAKE:', cur_take)
        if cur_take is None:
            self.update_take.emit(None)
            self.update_board_state.emit(BoardState.TAKE_ACTIVE)
            return
        print('CURTAKE_PLAYER:', cur_take.player.name)

        def no_new_take(tk):
            return tk.size() == 3 and self.game.get_current_player().get_darts_left() > 0

        keep_old_take_until_first_dart = True

        if no_new_take(cur_take):
            if keep_old_take_until_first_dart:
                self.update_take.emit(self.game.get_last_player().get_current_take())
            else:
                self.update_take.emit(None)
        else:
            self.update_take.emit(cur_take)

        # FOR THE CAMERA_SYSTEM
        if cur_take.is_complete():
            self.update_board_state.emit(BoardState.REMOVE_DARTS)
        else:
            self.update_board_state.emit(BoardState.TAKE_ACTIVE)

    def process_clicked_dart(self, point: QPointF):
        if self.game is not None and not self.game.is_blocked():
            self.process_dart(Dart(None, hit_location=point))

    def process_updated_dart(self, dart: Dart):
        if self.game is not None and not self.game.is_blocked():
            self.game.process_updated_dart(dart)
            self.game.updated.emit()

    @staticmethod
    def add_new_player(name) -> Union[Player, None]:
        return DatabaseController.add_new_player(name)

    def process_dart(self, dart: Dart):
        print("received dart", DartBoard.get_throw_result(dart.hit_location))
        if self.game.is_blocked():
            # print('controller ignores darts for blocked games....')
            return
        if not self.game.is_initialized:
            # print('controller ignores darts for uninitialized games....')
            return
        if self.game.winner is not None:
            # print('controller ignores darts for finished games....')
            return
        print('######> game add dart')
        self.game.add_dart(dart)

    @pyqtSlot()
    def received_update(self):
        import threading
        print('   >>>>>>>>>>>>>> UPDATE IN', threading.get_ident())
        DatabaseController.update_entity(self.game)
        self.propagate_current_state()
        self.game_updated.emit(self.game, False)

    @pyqtSlot(list)
    def game_action_request(self, actions):
        for a in actions:
            a()

    def _unload_current_game(self):
        if self.game is not None:
            self.game.updated.disconnect(self.received_update)
            self.game.action_request.disconnect(self.game_action_request)
            for player in self.game.players:
                player._current_leg_takes = None
                player._current_game_takes = None
                player._current_take = None
                player._current_game = None

    def load_game(self, game):
        print('loading', game, game.start_time, [p.get_current_game_takes().__len__() for p in game.players])
        self._unload_current_game()
        self.game = game
        if self.game.is_blocked():
            print('UNBLOCKING')
            from database.types import GameStatus
            self.game.status = GameStatus.IN_PROGRESS
            self.game._next_player(skip_introduce=True)
        self.game._recalculate_leg_scores()
        for player in self.game.get_players():
            SoundController.ensure_player_sound_file(player)
            player._current_leg_takes = None
            player._current_game_takes = None
            player._current_take = None
            player._current_game = self.game
            if game.get_current_player() == player:
                print(player.name, 'is on')
                if player.get_current_take() is None or player.get_current_take().is_complete():
                    print('fresh take -> dl=3')
                    player.darts_left = 3
                else:
                    print('existing take -> ')
                    player.darts_left = 3 - player.get_current_take().size()
            else:
                player.darts_left = 0
        self.game.updated.connect(self.received_update)
        self.game.action_request.connect(self.game_action_request)
        self.game_updated.emit(self.game, True)
        self.propagate_current_state()

    def request_new_game(self):
        def start_game(options):
            players = DatabaseController.get_players()
            self.request_multi_select.emit('Select Players', players, self.new_game, options)

        dialog = GameCreationDialog()
        dialog.game_configured.connect(start_game)
        dialog.exec_()

    def new_game(self, players, game_info):
        self._unload_current_game()
        print(game_info)
        game = DatabaseController.new_game(**game_info)
        self.game = game
        self.game.updated.connect(self.received_update)
        self.game.action_request.connect(self.game_action_request)
        self.game.start(players)
        print('#>>>>>>>>>>> before update entity', self.game.player_turn)
        DatabaseController.update_entity(self.game)
        print('#>>>>>>>>>>>>> after update', self.game.player_turn)
        self.game.players = self.game.get_players()
        self.propagate_current_state()
        self.game_updated.emit(self.game, True)

    @pyqtSlot()
    def request_takeback(self):
        if self.game.is_blocked():
            # print('controller ignores undo-action for blocked games....')
            return
        self.game.undo_dart()



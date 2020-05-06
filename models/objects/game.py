import datetime
from threading import Lock, Thread
from typing import List, Union

from sqlalchemy import Column, Enum, DateTime, JSON, Integer, ForeignKey, String, orm
from sqlalchemy.orm import relationship, make_transient

from database import BaseObject
from database.types import GameStatus, TakeResult
from models.helper import create_id_column, SignalWrapper, Option
from models.objects.leg import Leg
from models.objects.take import Take
from models.objects.dart import Dart
from models.objects.set import Set
from models.objects.game_players import GamePlayers
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class Game(BaseObject.Base):
    __tablename__ = 'games'
    id = create_id_column('game')
    status = Column(Enum(GameStatus), default=GameStatus.UNINITIALIZED)
    start_time = Column(DateTime)
    player_turn = Column(Integer, default=0)
    legs_to_set = Column(Integer, default=3)
    sets_to_match = Column(Integer, default=1)
    winner_id = Column(Integer, ForeignKey('players.id'))
    winner = relationship('Player')
    players = relationship('Player', secondary='game_players', back_populates='games')  # type: List[Player]
    game_players = relationship('GamePlayers', back_populates='game')  # type: List[GamePlayers]
    sets = relationship('Set', order_by=Set.start_time, back_populates='game', lazy='joined')  # type: List[Set]
    type = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity': 'games',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }
    updated = SignalWrapper()
    action_request = SignalWrapper(list)
    _undo_lock = Lock()
    enable_blocking = True
    player_scores = {}

    @classmethod
    def get_option_list(cls) -> List[Option]:
        return [
            Option('legs_to_set', int, list(range(1, 10))),
            Option('sets_to_match', int, list(range(1, 10)))
        ]

    def get_name(self):
        return self.__class__.__name__

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.now()
        self._set_defaults()

    def _set_defaults(self):
        self._undo_lock = Lock()
        self.enable_blocking = True
        self.players = self.get_players()

    @orm.reconstructor
    def init_on_load(self):
        # print('INIT ON LOAD', self, self.id, self.is_blocked())
        self._set_defaults()

    def __repr__(self):
        return '{id}: {type} - {start_time}'.format(**self.__dict__)

    def create_game_info_widget(self, parent) -> GameInfoWidget:
        raise NotImplementedError("You must return a game-info-widget or None")

    # noinspection PyMethodMayBeStatic
    def create_player_widget(self, player, parent) -> "PlayerWidget":
        from widgets.player_widget import PlayerWidget
        return PlayerWidget(player, parent=parent)

    def start(self, players: List["Player"]) -> None:
        print('>>>>>>>>PLAYERS: ', players)
        self.status = GameStatus.IN_PROGRESS
        game_players = [GamePlayers(self, player, players.index(player)) for player in players]

        from controllers.database_controller import DatabaseController
        DatabaseController._session.add_all(game_players)
        DatabaseController._session.commit()
        self.players = self.get_players()

        for player in self.players:
            player._current_game = self
            player._current_game_takes = None
            player._current_leg_takes = None
            player._current_take = None
            from controllers.sound_controller import SoundController
            SoundController.ensure_player_sound_file(player)
        DatabaseController._session.add_all(self.players)
        DatabaseController._session.commit()
        self.player_turn = 0
        self.add_set(self.get_current_player())
        self._next_player()
        print('> before update entity:', self.player_turn)
        DatabaseController.update_entity(self)
        print('> after update entity:', self.player_turn)
        self.players = self.get_players()
        print('started game of', self.__class__.__name__, 'with', [p.name for p in players])

    def get_current_set(self) -> "Set":
        return self.sets[-1]

    def get_current_leg(self) -> "Leg":
        return self.get_current_set().legs[-1]

    def get_current_take(self) -> Union["Take", None]:
        try:
            return self.get_current_leg().takes[-1]
        except IndexError:
            return None

    def get_players(self) -> List["Player"]:
        pls = {gp.player_index: gp.player for gp in self.game_players}
        return [pls[i] for i in range(len(self.game_players))]

    def get_current_player(self) -> "Player":
        return self.get_players()[self.player_turn]

    def get_last_player(self) -> "Player":
        return self.get_player_before(self.get_current_player())

    def get_player_before(self, player: "Player") -> "Player":
        p_idx = self.get_players().index(player)
        if abs(p_idx - 1) > len(self.get_players()):
            return self.get_players()[0]
        return self.get_players()[p_idx - 1]

    def get_player_after(self, player: "Player") -> "Player":
        p_idx = self.get_players().index(player)
        return self.get_players()[p_idx + 1 if p_idx < (len(self.get_players()) - 1) else 0]

    def _next_player(self, sound_jobs=None, skip_introduce=False) -> None:
        print('#>#> pt before:', self.player_turn)
        self.player_turn = self.player_turn + 1 if self.player_turn < (len(self.get_players()) - 1) else 0
        print('#>#> pt after:', self.player_turn)
        player = self.get_current_player()
        player.darts_left = 3
        if not skip_introduce:
            from controllers.sound_controller import SoundController, SoundJob
            introduce = SoundJob.from_player_name(player)
            print('introducing player', self.player_turn, self.get_current_player().name)
            # introduce.delay_ms = 2000
            jobs = [introduce]
            if sound_jobs:
                jobs.extend(sound_jobs)
            SoundController.instance().play_job_series(jobs)

    def add_set(self, beginner: "Player"):
        set = Set(self, beginner)
        self.add_leg(set, beginner)
        self.sets.append(set)

    def add_leg(self, set: "Set", beginner: "Player"):
        print('player-turn before set-leg', self.player_turn)
        leg = Leg(set, beginner)
        # set to player before actual starter, because we will always call '_next player' before continuing
        self.player_turn = self.get_players().index(self.get_player_before(beginner))
        print('player_turn after set-leg:', self.player_turn)
        for player in self.get_players():
            player._current_game_takes = None
            player._current_leg_takes = None

    def _complete_take(self, take: "Take", result: TakeResult):
        print('>> completing take')
        take.player.darts_left = 0
        from controllers.database_controller import DatabaseController
        DatabaseController.complete_take(take, result)
        if result == TakeResult.WIN:
            self._complete_leg(take.leg, take.player)

    def _complete_leg(self, leg: "Leg", winner: "Player"):
        print('>> completing leg')
        from controllers.database_controller import DatabaseController
        DatabaseController.complete_leg(leg, winner)
        if self.legs_to_set == sum([1 for winning_leg in leg.set.legs if winning_leg.winner == winner]):
            self._complete_set(leg.set, winner)

    def _complete_set(self, set: "Set", winner: "Player"):
        print('>> completing set')
        from controllers.database_controller import DatabaseController
        DatabaseController.complete_set(set, winner)
        if self.sets_to_match == sum([1 for winning_set in self.sets if winning_set.winner == winner]):
            self._complete_game(winner)

    def _prepare_next_leg(self):
        next_player = self.get_player_after(self.get_current_leg().beginner)
        self.add_leg(self.get_current_set(), next_player)
        from controllers.database_controller import DatabaseController
        DatabaseController.update_entity(self)

    def _prepare_next_set(self):
        next_player = self.get_player_after(self.get_current_set().beginner)
        self.add_set(next_player)
        from controllers.database_controller import DatabaseController
        DatabaseController.update_entity(self)

    def _complete_game(self, winner: "Player"):
        from controllers.database_controller import DatabaseController
        DatabaseController.complete_game(self, winner)

    def _remove_last_leg(self):
        from controllers.database_controller import DatabaseController
        leg = self.get_current_leg()
        if len(leg.takes) == 0:
            self.get_current_set().legs.remove(leg)
            print('removing leg', leg)
            DatabaseController.remove_leg(leg)
            set = self.get_current_set()
            if len(self.sets) > 1 and len(set.legs) == 0:
                self.sets.remove(set)
                print('removing set', set)
                DatabaseController.remove_set(set)
            print('new cs, new cl, playerturn, cl_winner', self.get_current_set(), self.get_current_leg(), self.player_turn, self.get_current_leg().winner.name)
            self.player_turn = self.get_players().index(self.get_player_after(self.get_current_leg().winner))  # will be reduced by one afterwards
            print('new playerturn:', self.player_turn)
            for player in self.players:
                player._current_game_takes = None
                player._current_leg_takes = None
                player._current_take = None
        DatabaseController.update_entity(self)

    def _recalculate_leg_scores(self):
        raise NotImplementedError("You must implement this Method. "
                                  "Store the results in self.player_scores: Dict[Player, int]")

    def get_player_score(self, player: "Player") -> int:
        if player not in self.player_scores:
            self._recalculate_leg_scores()
        return self.player_scores[player]

    def has_darts(self) -> bool:
        try:
            self.sets[0].legs[0].takes[0].darts[0]
        except IndexError:
            return False
        return True

    def is_initialized(self) -> bool:
        return self.status != GameStatus.UNINITIALIZED

    def is_finished(self) -> bool:
        return self.status == GameStatus.FINISHED

    def set_finished(self):
        self.status = GameStatus.FINISHED

    def set_in_progress(self):
        self.status = GameStatus.IN_PROGRESS

    def is_blocked(self) -> bool:
        return self.status == GameStatus.BLOCKING

    def generate_next_dart(self) -> "Dart":
        raise NotImplementedError("You must implement this Method")

    def _internal_handle_take_completion(self, player: "Player", updated=False):
        self._recalculate_leg_scores()
        self._handle_take_completion(player, updated)
        self._recalculate_leg_scores()

    def _handle_take_completion(self, player: "Player", updated=False):
        raise NotImplementedError("You must implement this Method. "
                                  "It should check whether the current take is completed,"
                                  "and call self._complete_take() with the appropriate RESULT")

    def _announce_take_result(self, score: int):
        pass

    def process_updated_dart(self, dart: Dart):
        take = dart.take
        idx = take.darts.index(dart)
        take.result = None
        from controllers.database_controller import DatabaseController

        tmp_darts = []
        print('TDARTS:', take.darts, 'dart_to_change:', dart,'idx:', idx)
        for i in range(idx+1, len(take.darts)):
            td = take.darts.pop(idx+1)
            td.take = None
            td.take_id = None
            DatabaseController._session.query(Dart).filter(Dart.id == td.id).delete()
            DatabaseController._session.commit()
            print('deleted', td)
            tmp_darts.append(td)
        print('take updated:', take.darts, 'deleted darts:', [(d, d.take_id, d.take) for d in tmp_darts])
        self._internal_handle_take_completion(take.player, updated=True)
        self._recalculate_leg_scores()
        for td in tmp_darts:
            if take.result is None:
                td.take_id = take.id
                make_transient(td)
                td.take = take
                DatabaseController._session.commit()
                # td.take = take
                self._internal_handle_take_completion(take.player, updated=True)
            else:
                del td

        self.updated.emit()

    def add_dart(self, dart: "Dart") -> None:
        with self._undo_lock:
            self._add_dart_to_player(dart, self.get_current_player())

    def _add_dart_to_player(self, dart: "Dart", player: "Player"):
        from controllers.database_controller import DatabaseController
        if not player.get_current_leg_takes() or player.get_current_take().is_complete():
            take = DatabaseController.new_take(player, self.get_current_leg())
            DatabaseController.new_dart(take, dart)
            player._current_game_takes = None
            player._current_leg_takes = None
            player.darts_left -= 1
        else:
            take = player.get_current_take()
            DatabaseController.new_dart(take, dart)
            player.darts_left -= 1
        DatabaseController.update_entity(take)
        player._current_take = take
        self._internal_handle_take_completion(player)
        cur_take = player.get_current_take()
        if cur_take.is_complete():
            def take_completion(score, game_winner=None, set_winner=None, leg_winner=None):
                from controllers.sound_controller import SoundController, SoundSeries, SoundJob
                with self._undo_lock:
                    self._announce_take_result(score)
                    if game_winner is not None:
                        print('GAME WON!')
                        self.action_request.emit([self.set_finished])
                        SoundController.instance().play_job_series(SoundSeries.from_sound_file_game_shot(game_winner))
                    elif set_winner is not None:
                        print('SET WON!')
                        SoundController.instance().play_job_series(SoundSeries.from_sound_file_set_shot(set_winner),
                                                                   blocking=self.enable_blocking)
                        self.action_request.emit([self._prepare_next_set,
                                                  self.set_in_progress,
                                                  self._recalculate_leg_scores,
                                                  self._next_player])
                    elif leg_winner is not None:
                        print('LEG WON!')
                        SoundController.instance().play_job_series(SoundSeries.from_sound_file_leg_shot(leg_winner),
                                                                   blocking=self.enable_blocking)
                        self.action_request.emit([self._prepare_next_leg,
                                                  self.set_in_progress,
                                                  self._recalculate_leg_scores,
                                                  self._next_player])
                    else:
                        self.action_request.emit([self.set_in_progress,
                                                  self._recalculate_leg_scores,
                                                  self._next_player])
                    self.updated.emit()
            print('############### SET BLOCKING!')
            self.status = GameStatus.BLOCKING
            Thread(target=take_completion,
                   kwargs={
                       'score': cur_take.get_score(),
                       'game_winner':
                           self.winner.sound_file if self.winner else None,
                       'set_winner':
                           self.get_current_set().winner.sound_file if self.get_current_set().winner else None,
                       'leg_winner':
                           self.get_current_leg().winner.sound_file if self.get_current_leg().winner else None,
                   }).start()

        self.updated.emit()

    def undo_dart(self) -> None:
        # print('###################### UNDO DART CALLED ########################')
        from controllers.database_controller import DatabaseController

        def revisit_take(take: Take, dart: Dart):
            if take is not None:  # if there was no deletion
                if take.size() == 0:
                    print('deleting take', take, take.id)
                    take.player._current_leg_takes = None
                    take.player._current_game_takes = None
                    DatabaseController.remove_take(take)

                else:
                    DatabaseController.remove_dart(dart)

        with self._undo_lock:
            cur_p = self.get_current_player()

            # no darts in game -> return
            # no darts in current leg -> remove last dart of winner of last leg
            # ELSE
            #

            if not self.has_darts():
                # print('game not started yet')
                return
            else:

                if len(self.get_current_leg().takes) < 1:
                    if len(self.get_current_set().legs) > 1:
                        last_p = self.get_current_set().legs[-2].winner
                    else:
                        last_p = self.sets[-2].winner
                else:
                    last_p = self.get_last_player()
                print('checking state.')
                print('curP cur take, lastP cur take', cur_p.get_current_take(), last_p.get_current_take())
            if self.is_finished() or (cur_p.get_current_take() is not None
                                      and cur_p.get_current_take().size() > 0
                                      and 0 < cur_p.darts_left < 3):
                print('remove CURRENT LAST')
                revisit_take(*cur_p.remove_last_dart())
                print(cur_p.name, 'setting player takes to NONE')
                cur_p._current_game_takes = None
                cur_p._current_take = None
                self.winner = None
                self.get_current_leg().winner = None
                self.get_current_set().winner = None
                self.status = GameStatus.IN_PROGRESS
                self._recalculate_leg_scores()
                self.updated.emit()
            elif last_p.get_current_take() is not None\
                    and last_p.get_current_take().size() > 0:
                print('remove LAST last')
                cur_p.darts_left = 0
                revisit_take(*last_p.remove_last_dart())
                print('DECREASE PLAYER TURN FROM ', self.player_turn)
                self.player_turn = self.player_turn - 1 if self.player_turn > 0 else len(self.players) - 1
                print('TO', self.player_turn)
                self.winner = None
                self.get_current_leg().winner = None
                self.get_current_set().winner = None
                self.status = GameStatus.IN_PROGRESS
                print(self.get_current_player().name, 'setting player takes to NONE')
                self.get_current_player()._current_game_takes = None
                self.get_current_player()._current_take = None
                self._recalculate_leg_scores()
                self.updated.emit()
            else:
                print('WEIRD', self.is_finished(),
                      self.get_current_player().get_current_take().size(),
                      self.get_current_player().darts_left)


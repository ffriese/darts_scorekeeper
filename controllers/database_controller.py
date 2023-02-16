from typing import List, Type, Union

from PyQt5.QtCore import QObject

from sqlalchemy import event, exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database import BaseObject
from database.types import GameStatus, TakeResult, GameVariant
from models.objects.leg import Leg
from models.objects.take import Take
from models.objects.dart import Dart
from models.objects.set import Set
from models.objects.player import Player
from models.objects.game import Game

# noinspection PyUnresolvedReferences
import models.objects.games  # needed for sql-alchemy to create all games
# noinspection PyUnresolvedReferences
from models.objects.games import x01, cricket, around_the_clock

Base = BaseObject.Base


def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('PRAGMA FOREIGN_KEYS=ON;')


def _create_session(engine):
    print('INIT DB SESSION')
    session = sessionmaker()
    event.listen(engine, 'connect', _fk_pragma_on_connect)
    Base.metadata.create_all(engine, checkfirst=True)
    session.configure(bind=engine)
    created_session = session()
    created_session.commit()
    return created_session


class DatabaseController(QObject):
    _engine = create_engine('sqlite:///alchemy.db')  # , echo='debug')
    _session = _create_session(_engine)  # type: Session
    _session.autoflush = False

    @staticmethod
    def get_players() -> List[Player]:
        players = DatabaseController._session.query(Player).all()
        for player in players:
            DatabaseController.update_entity(player)
        return players

    @staticmethod
    def add_new_player(name: str) -> Union[Player, None]:
        p = Player(name=name)
        try:
            DatabaseController._session.add(p)
            DatabaseController._session.commit()
            return p
        except exc.IntegrityError:
            DatabaseController._session.rollback()
            return None

    @classmethod
    def get_unfinished_games(cls) -> List[Game]:
        games = DatabaseController._session.query(Game).filter(Game.status.isnot(GameStatus.FINISHED)).all()
        # print('LOADING UNFINISHED GAMES')
        # for game in games:
        #     print('GD', game.__dict__)
        return games

    @classmethod
    def get_games(cls) -> List[Game]:
        games = DatabaseController._session.query(Game).all()
        return games

    @staticmethod
    def new_game(game_type: Type[Game], *args, **kwargs) -> Game:
        print(args, kwargs)
        game = game_type(*args, **kwargs)
        DatabaseController._session.add(game)
        DatabaseController._session.commit()
        return game

    @staticmethod
    def new_set(game: Game, beginner: Player) -> Set:
        set = Set(game, beginner)
        DatabaseController._session.add(set)
        DatabaseController._session.commit()
        return set

    @staticmethod
    def new_leg(set: Set, beginner: Player) -> Leg:
        leg = Leg(set, beginner)
        DatabaseController._session.add(leg)
        DatabaseController._session.commit()
        return leg

    @staticmethod
    def new_take(player: Player, leg: Leg) -> Take:
        take = Take(leg, player)
        DatabaseController._session.add(take)
        DatabaseController._session.commit()
        return take

    @staticmethod
    def new_dart(take: Take, dart: Dart) -> Dart:
        if dart.take is None or dart.take.id != take.id:
            dart.take = take
        DatabaseController._session.add(dart)
        DatabaseController._session.commit()
        return dart

    @staticmethod
    def complete_take(take: Take, result: TakeResult):
        take.result = result
        DatabaseController._session.add(take)
        DatabaseController._session.commit()

    @staticmethod
    def complete_leg(leg: Leg, winner: Player):
        leg.winner = winner
        DatabaseController._session.add(leg)
        DatabaseController._session.commit()

    @staticmethod
    def complete_set(set: Set, winner: Player):
        set.winner = winner
        DatabaseController._session.add(set)
        DatabaseController._session.commit()

    @staticmethod
    def complete_game(game: Game, winner: Player):
        game.winner = winner
        DatabaseController._session.add(game)
        DatabaseController._session.commit()

    @staticmethod
    def remove_dart(dart: Dart):
        with DatabaseController._session.no_autoflush:
            DatabaseController._session.query(Dart).filter(Dart.id == dart.id).delete()
            DatabaseController._session.commit()

    @staticmethod
    def remove_take(take: Take):
        with DatabaseController._session.no_autoflush:
            DatabaseController._session.query(Dart).filter(Dart.take_id == take.id).delete()
            DatabaseController._session.query(Take).filter(Take.id == take.id).delete()
            DatabaseController._session.commit()

    @staticmethod
    def remove_leg(leg: Leg):
        with DatabaseController._session.no_autoflush:
            for take in leg.takes:
                DatabaseController._session.query(Dart).filter(Dart.take_id == take.id).delete()
                DatabaseController._session.query(Take).filter(Take.id == take.id).delete()
            DatabaseController._session.query(Leg).filter(Leg.id == leg.id).delete()
            DatabaseController._session.commit()

    @staticmethod
    def remove_set(set: Set):
        with DatabaseController._session.no_autoflush:
            for leg in set.legs:
                for take in leg.takes:
                    DatabaseController._session.query(Dart).filter(Dart.take_id == take.id).delete()
                    DatabaseController._session.query(Take).filter(Take.id == take.id).delete()
                DatabaseController._session.query(Leg).filter(Leg.id == leg.id).delete()
            DatabaseController._session.query(Set).filter(Set.id == set.id).delete()
            DatabaseController._session.commit()

    @staticmethod
    def update_entity(entity):
        with DatabaseController._session.no_autoflush:
            DatabaseController._session.add(entity)
            DatabaseController._session.commit()
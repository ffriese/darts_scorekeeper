import datetime
from typing import List

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QAbstractItemView, QListWidgetItem, QPushButton, \
    QHBoxLayout, QLabel, QInputDialog, QMessageBox, QCheckBox, QSpinBox, QComboBox, QLineEdit, QFormLayout
from sqlalchemy import ColumnDefault

# noinspection PyUnresolvedReferences
from database.types import GameStatus
from models.objects.games import x01, cricket, around_the_clock
from models.objects.game import Game


class GameCreationDialog(QDialog):

    game_configured = pyqtSignal(dict)

    @staticmethod
    def get_gui_element_for_type(type: type, options=None, default=None):
        element = None
        if type == bool:
            element = QCheckBox()
            element.setProperty('cur_value', lambda x=element: element.isChecked())
            if default is not None:
                element.setChecked(default)
        elif type == int:
            element = QSpinBox()
            element.setProperty('cur_value', lambda x=element: element.value())
            if options:
                element.setMinimum(min(options))
                element.setMaximum(max(options))
            if default:
                element.setValue(default)
        elif type == str:
            if options is None:
                element = QLineEdit()
                element.setProperty('cur_value', lambda x=element: element.text())
                if default:
                    element.setText(default)
            else:
                element = QComboBox()
                element.setProperty('cur_value', lambda x=element: element.currentText())
                for o in options:
                    element.addItem(o)
                if default:
                    element.setCurrentText(default)
        return element

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = None
        self.layout = QVBoxLayout()
        self.option_layout = QFormLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(QIcon('img/new-icon.png'))
        self.setWindowTitle("New Game")
        self.game_box = QComboBox()
        self.accept_button = QPushButton('Start Game')
        self.accept_button.clicked.connect(self.start_game)
        self.layout.addWidget(self.game_box)
        self.layout.addLayout(self.option_layout)
        self.layout.addWidget(self.accept_button)
        self.options = {}
        self.available_games = {game.__name__: game for game in Game.__subclasses__()}  # type: Dict[str, Type[Game]]
        for game in self.available_games.keys():
            self.game_box.addItem(game)
        self.game_box.setCurrentText('X01')
        self.set_game('X01')
        self.game_box.currentTextChanged.connect(self.set_game)

    def set_game(self, game_name):
        game = self.available_games[game_name]

        self.options = {}
        print('row-count:', self.option_layout.rowCount())
        while self.option_layout.rowCount() > 0:
            self.option_layout.removeRow(0)

        print('row-count after:', self.option_layout.rowCount())

        options = game.get_option_list()
        for option in options:
            default = getattr(game, option.name).default  # type: ColumnDefault
            element = self.get_gui_element_for_type(option.type,
                                                    option.options,
                                                    default.arg if default is not None else None)
            self.option_layout.addRow(option.name,
                                      element)
            self.options[option.name] = element
            print('added row')

    def start_game(self):
        options = {'game_type': self.available_games[self.game_box.currentText()]}
        for o in self.options:
            options[o] = self.options[o].property('cur_value')()
        print(options)
        self.game_configured.emit(options)
        self.close()


class GameSelectionDialog(QDialog):

    game_selected = pyqtSignal(Game)

    def __init__(self, title: str, games: List[Game], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.games = games
        self.setMinimumSize(QSize(650, 400))
        self.setWindowIcon(QIcon('img/application-get-icon.png'))
        self.setWindowTitle(title)
        self.gameListWidget = QListWidget()
        self.gameListWidget.itemSelectionChanged.connect(self.selected)
        self.infoWidget = QLabel('no game selected')
        self.accept_button = QPushButton('Load')
        self.accept_button.clicked.connect(self.load_game)
        self.accept_button.setEnabled(False)
        self.layout = QHBoxLayout()
        self.vlay = QVBoxLayout()
        self.layout.addWidget(self.gameListWidget)
        self.layout.addLayout(self.vlay)
        self.vlay.addWidget(self.infoWidget)
        self.vlay.addWidget(self.accept_button)
        self.stored_games = {}
        self.set_games(self.games)
        self.setLayout(self.layout)

    def game_repr(self, game: Game):
        return '%s - %s' % (game.get_name(), game.start_time.ctime())

    def set_games(self, games: List[Game]):
        self.gameListWidget.clear()
        self.stored_games = {}
        for game in games:
            item = QListWidgetItem(self.game_repr(game))
            item.setData(QtCore.Qt.UserRole, game.id)
            if game.status == GameStatus.FINISHED:
                item.setForeground(QtCore.Qt.gray)
            self.stored_games[game.id] = game
            self.gameListWidget.addItem(item)

    def selected(self):
        if self.gameListWidget.selectedItems():
            item = self.gameListWidget.selectedItems()[0]
            game = self.stored_games[item.data(QtCore.Qt.UserRole)]
            self.infoWidget.setText('%s\n_______________\n\nPlayers:\n\n%s\n\n_______________\nState:\n\n%s'
                                    % (self.game_repr(game),
                                       '\n'.join(['%s - %s [Sets:%s/%s, Legs:%s/%s]' % (
                                           p.name, game.get_player_score(p),
                                           sum([1 for set in game.sets if set.winner == p]),
                                           game.sets_to_match,
                                           sum([1 for leg in game.get_current_set().legs if leg.winner == p]),
                                           game.legs_to_set
                                       )
                                                  for p in game.get_players()]),
                                       game.status))
            self.accept_button.setEnabled(True)
        else:
            self.accept_button.setEnabled(False)

    def load_game(self):
        if self.gameListWidget.selectedItems():
            item = self.gameListWidget.selectedItems()[0]
            game = self.stored_games[item.data(QtCore.Qt.UserRole)]
            self.game_selected.emit(game)
            self.close()


class PlayerSelectionDialog(QDialog):
    players_selected = pyqtSignal(list)
    added_player = pyqtSignal(str)

    def __init__(self, options, parent=None):
        super(PlayerSelectionDialog, self).__init__(parent)
        self.all_player_layout = QVBoxLayout()
        self.game_player_layout = QVBoxLayout()
        self.layout = QHBoxLayout()
        self.layout.addLayout(self.all_player_layout)
        self.layout.addLayout(self.game_player_layout)
        self.allPlayerWidget = QListWidget()
        self.gamePlayerWidget = QListWidget()
        self.gamePlayerWidget.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.gamePlayerWidget.setDragDropMode(QAbstractItemView.InternalMove)
        self.gamePlayerWidget.setGeometry(QtCore.QRect(10, 10, 211, 291))
        self.gamePlayerWidget.itemDoubleClicked.connect(self.remove_selected_player)
        for o in options:
            item = QListWidgetItem(str(o))
            self.allPlayerWidget.addItem(item)
        self.allPlayerWidget.itemClicked.connect(self.move_over)
        self.all_player_layout.addWidget(QLabel("Available Players"))
        self.game_player_layout.addWidget(QLabel("Selected Players"))
        self.all_player_layout.addWidget(self.allPlayerWidget)
        self.game_player_layout.addWidget(self.gamePlayerWidget)

        self.accept_button = QPushButton("Ok")
        self.accept_button.setEnabled(False)
        self.accept_button.clicked.connect(self.select_players)

        self.add_player_button = QPushButton("Add Player")
        self.add_player_button.clicked.connect(self.add_player)

        self.game_player_layout.addWidget(self.accept_button)
        self.all_player_layout.addWidget(self.add_player_button)
        self.setLayout(self.layout)

    def move_over(self):
        item = self.sender().selectedItems()[0]
        current_players = [self.gamePlayerWidget.item(i).text() for i in range(self.gamePlayerWidget.count())]
        if item.text() in current_players:
            self.gamePlayerWidget.takeItem(current_players.index(item.text()))
            if self.gamePlayerWidget.count() < 1:
                self.accept_button.setEnabled(False)
        else:
            item = QListWidgetItem(item.text())
            self.gamePlayerWidget.addItem(item)
            self.accept_button.setEnabled(True)

    def remove_selected_player(self, item):
        current_players = [self.gamePlayerWidget.item(i).text() for i in range(self.gamePlayerWidget.count())]
        self.gamePlayerWidget.takeItem(current_players.index(item.text()))
        if self.gamePlayerWidget.count() < 1:
            self.accept_button.setEnabled(False)

    def select_players(self):
        players = [str(self.gamePlayerWidget.item(i).text()) for i in range(self.gamePlayerWidget.count())]
        self.players_selected.emit(players)
        self.close()

    def add_player(self):
        text, accepted = QInputDialog.getText(self, 'Add Player', 'Player-Name:')
        if accepted:
            self.added_player.emit(text)

    def new_player_accepted(self, name):
        item = QListWidgetItem(name)
        self.allPlayerWidget.addItem(item)

    def show_error(self, title, msg):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(msg)
        box.exec_()

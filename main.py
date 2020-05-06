#
# pyinstaller --noconsole --onedir --windowed --icon=img/dart.ico --add-data="img/*;img" --add-data="sounds/*;sounds" --add-data="fonts/*;fonts" --hidden-import sqlalchemy.ext.baked --hidden-import pkg_resources.py2_warn --noconfirm main.py

import sys

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QKeyEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QStatusBar, QLabel, QMenuBar, QAction, QDialog, QInputDialog, \
    QPushButton

from controllers.main_controller import MainController
from logic.settings import Settings
from widgets.active_game_widget import ActiveGameWidget
from widgets.dialogs import PlayerSelectionDialog, GameSelectionDialog


class App(QMainWindow):

    generate_request = pyqtSignal()
    take_back_request = pyqtSignal()

    def __init__(self):
        super().__init__()

        # basic window init
        # self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle('Play Darts')
        self.setWindowIcon(QIcon('img/dart.png'))
        # self.setStyleSheet('background-image: url(img/wood_bar.png)')
        self.setMinimumSize(800, 500)

        # status bar init
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Initializing...')

        self.game_info_widget = QLabel()
        self.statusBar.addPermanentWidget(self.game_info_widget)


        self.create_toggle_button('sound_toggle', QIcon('img/sound_on.png'), QIcon('img/sound_off.png'),
                                  self.sound_toggled, default=Settings.SOUND_ENABLED.get())
        self.create_toggle_button('dart_dot_toggle', QIcon('img/dart.png'), QIcon('img/dot.png'),
                                  self.dart_dot_toggled, default=Settings.DISPLAY_DARTS.get())

        self.mqtt_status_icon = QLabel()
        self.mqtt_status_icon.setPixmap(QPixmap("img/mqtt_off.png"))
        self.mqtt_status_icon.setToolTip("MQTT not connected")
        self.statusBar.addPermanentWidget(self.mqtt_status_icon)


        # create widgets
        self.active_game_widget = ActiveGameWidget()
        self.game_controller = MainController()

        # create menus
        self.gameMenu = self.menuBar().addMenu('Game')
        self.add_menu_action(self.gameMenu, 'New Game', self.game_controller.request_new_game,
                             icon=QIcon('img/application-add-icon.png'))
        self.add_menu_action(self.gameMenu, 'Load Game', self.game_controller.select_game_to_load,
                             icon=QIcon('img/application-get-icon.png'))

        self.editMenu = self.menuBar().addMenu('Edit')
        self.viewMenu = self.menuBar().addMenu('View')
        self.searchMenu = self.menuBar().addMenu('Search')
        self.toolsMenu = self.menuBar().addMenu('Tools')
        self.helpMenu = self.menuBar().addMenu('Help')

        self.connect_signals()

        self.setCentralWidget(self.active_game_widget)

        self.resize(800, 500)
        self.show()
        self.initialize()

    def initialize(self):
        self.game_controller.initialize()
        self.statusBar.showMessage('Ready')

    def add_menu_action(self, menu, text: str, slot, disabled=False, icon=None):
        action = QAction(text)
        if icon is not None:
            action.setIcon(icon)
        if disabled:
            action.setEnabled(False)
        setattr(self, text.replace(' ', '_').lower(), action)
        menu.addAction(action)
        action.triggered.connect(slot)

    def create_toggle_button(self, name: str, icon_on: QIcon, icon_off: QIcon, callback, default: bool = True):
        bt = QPushButton(icon_on if default else icon_off, '')
        bt.setProperty('icons', {True: icon_on, False: icon_off})
        bt.setCheckable(True)
        bt.setChecked(default)
        bt.toggled.connect(callback)
        setattr(self, name, bt)
        self.statusBar.addPermanentWidget(bt)

    def sound_toggled(self, status: bool):
        bt = self.sender()  # type: QPushButton
        bt.setIcon(bt.property('icons')[status])
        Settings.SOUND_ENABLED.set(status)

    def dart_dot_toggled(self, status: bool):
        bt = self.sender()  # type: QPushButton
        bt.setIcon(bt.property('icons')[status])
        Settings.DISPLAY_DARTS.set(status)
        # TODO: update_game

    def mqtt_status_changed(self, data: dict):
        connected = data.get('connected', False)
        host = data.get('host', None)
        self.mqtt_status_icon.setPixmap(QPixmap("img/%s.png" % ('mqtt_on' if connected else 'mqtt')))
        self.mqtt_status_icon.setToolTip("MQTT %s broker on %s" %
                                         ('connected to' if connected else 'trying to connect to',
                                          host))

    def game_updated(self, game: "Game", new_game:bool):
        if new_game:
            self.game_info_widget.setText('%s - %s' % (game.get_name(),
                                                        {o.name: getattr(game, o.name) for o in
                                                         game.get_option_list()}))
        else:
            self.statusBar.showMessage(str(game.status))

    def connect_signals(self):
        # game controller events
        self.game_controller.update_mqtt_status.connect(self.mqtt_status_changed)
        # self.game_controller.update_take.connect(self.active_game_widget.dartboard_widget.set_take)
        self.game_controller.update_take.connect(self.active_game_widget.set_take)
        self.game_controller.game_updated.connect(self.active_game_widget.update_game)
        self.game_controller.game_updated.connect(self.game_updated)

        # gui events
        self.active_game_widget.dartboard_widget.clicked_dart.connect(self.game_controller.process_clicked_dart)
        self.active_game_widget.dartboard_widget.updated_dart.connect(self.game_controller.process_updated_dart)

        self.generate_request.connect(self.game_controller.generate_dart)
        self.take_back_request.connect(self.game_controller.request_takeback)

        # dialogs

        self.game_controller.request_game_choice.connect(self.show_selection_dialog)
        self.game_controller.request_multi_select.connect(self.show_multi_selection_dialog)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_G:
            self.generate_request.emit()
        elif event.key() == Qt.Key_Backspace:
            self.take_back_request.emit()
        elif event.key() == Qt.Key_Control:
            Settings.DRAG_DARTS_ENABLED.set(False)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            Settings.DRAG_DARTS_ENABLED.set(True)

    def show_selection_dialog(self, title, games, result_function):

        def game_selected(game):
            result_function(game)

        gs_diag = GameSelectionDialog(title, games, parent=self)
        gs_diag.game_selected.connect(game_selected)
        gs_diag.exec_()
        # game_info = {game.__repr__(): game for game in games}
        # text, accepted = QInputDialog.getItem(self, title,
        #                                       'Game:',
        #                                       [game.__repr__() for game in games])
        # if accepted:
        #     game = game_info[text]
        #     result_function(game)

    def show_multi_selection_dialog(self, title, options, result_function, user_data):
        option_texts = {option.name: option for option in options}

        def trigger_result(res):
            result_function([option_texts[r] for r in res], user_data)

        def try_add_player(name):
            print('trying to add', name)
            player = self.game_controller.add_new_player(name)
            if player is not None:
                self.sender().new_player_accepted(player.name)
                option_texts[player.name] = player
            else:
                self.sender().show_error('Could not add Player', 'Name is already taken')

        ms = PlayerSelectionDialog(option_texts.keys())
        ms.setWindowTitle(title)
        ms.setWindowIcon(QIcon('img/group-icon.png'))
        ms.players_selected.connect(trigger_result)
        ms.added_player.connect(try_add_player)
        ms.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    app.aboutToQuit.connect(lambda: sys.exit(0))
    sys.exit(app.exec_())

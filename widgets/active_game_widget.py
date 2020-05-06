from collections import OrderedDict
from typing import List

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QResizeEvent, QPixmap, QPaintEvent, QPainter, QColor
from PyQt5.QtWidgets import QWidget

from models.objects.player import Player
from models.objects.take import Take
from models.objects.game import Game
from widgets.active_player_widget import ActivePlayerWidget
from widgets.dartboard_widget import DartboardWidget
from widgets.player_widget import PlayerWidget


class ActiveGameWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_image = QPixmap('img/wood.jpg')
        self.player_widgets = OrderedDict()  # type: OrderedDict[Player, PlayerWidget]
        self.dartboard_widget = DartboardWidget(self)
        self.active_widget_reference = None
        self.active_player_widget = ActivePlayerWidget(self)
        self.active_player_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.game_info_widget = None
        self.player_colors = [0xe6194B, 0x3cb44b, 0xffe119, 0x4363d8, 0xf58231, 0x911eb4, 0x42d4f4, 0xf032e6, 0xbfef45,
                              0xfabebe, 0x469990, 0xe6beff, 0x9A6324, 0xfffac8, 0x800000, 0xaaffc3, 0x808000, 0xffd8b1,
                              0x000075, 0xa9a9a9, 0xffffff, 0x000000]

    def update_game(self, game: Game, new_game: bool):
        if new_game:
            self.set_players(game, game.get_players())
            if self.game_info_widget is not None:
                self.game_info_widget.deleteLater()
            self.game_info_widget = game.create_game_info_widget(parent=self)
        self.active_widget_reference = None
        for pw in self.player_widgets.values():
            score = game.get_player_score(pw.player)
            active = pw.player == game.get_current_player()
            pw.set_player_score(score)
            if active:
                self.active_widget_reference = pw
                self.active_player_widget.set_player(pw.player, score)
            pw.repaint()
        self.redraw(self.width(), self.height())
        self.game_info_widget.update_players(game.get_players())

    def set_players(self, game: Game, players: List[Player]):
        for pw in self.player_widgets.values():
            pw.deleteLater()
        self.player_widgets.clear()
        for i, player in enumerate(players):
            player.color = QColor(self.player_colors[i % len(self.player_colors)])
            self.player_widgets[player] = game.create_player_widget(player, parent=self)
        self.redraw(self.width(), self.height())

    def set_take(self, take: Take):
        self.dartboard_widget.set_darts(take.darts if take is not None else [])
        self.active_player_widget.set_take(take)

    def redraw(self, w, h):
        side = int(min(w * 4 / 7, h - 20))
        board_x = w - side - 10
        pwh = self.height() / (len(self.player_widgets) + 1)
        self.dartboard_widget.setGeometry(board_x, 10, side, side)
        gww = w / 5
        self.active_player_widget.setGeometry(board_x-gww, int(h*(3.0/4.0)), w-(board_x-gww), int(h/4))
        if self.game_info_widget is not None:
            self.game_info_widget.setGeometry(board_x - gww, 10, gww, 0.75 * h - 20)
        for i, player_widget in enumerate(self.player_widgets.values()):
            offset = 10 if player_widget == self.active_widget_reference else 0
            player_widget.setGeometry(offset+5, i * (pwh + 5) + 5, board_x - gww - 15, pwh)
            player_widget.repaint()

    def resizeEvent(self, event: QResizeEvent):
        w = event.size().width()
        h = event.size().height()
        self.redraw(w, h)
        event.accept()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.drawPixmap(QRect(0, 0, self.background_image.width(), self.background_image.height()),
                           self.background_image)
        event.accept()

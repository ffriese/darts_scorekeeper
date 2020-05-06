import itertools

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt, QRectF
from PyQt5.QtGui import QResizeEvent, QPaintEvent, QPainter, QPixmap, QPainterPath, QFont, QBrush, QFontMetrics, QColor, \
    QTransform
from PyQt5.QtWidgets import QWidget, QLabel, QComboBox

from models.objects.player import Player
from widgets.dartboard_widget import DartboardWidget
from widgets import painter_helper


class MatchProgressWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_sets = 1
        self.total_legs = 1
        self.sets = 0
        self.legs = 0
        self.darts = 0

    def paintEvent(self, event: QPaintEvent):
        side = int(min(self.height(), self.width() / 2))
        painter = QPainter()
        painter.begin(self)
        dartw = side
        margin = 5
        barw = self.width() - dartw - (2 * margin)
        barh = self.height() / 5
        painter.fillRect(QRect(*(int(v) for v in (margin,
                                                  barh,
                                                  barw,
                                                  barh))),
                         QColor(25, 25, 25, 100))
        painter.fillRect(QRect(*(int(v) for v in (margin*1.05,
                                                  barh*1.05,
                                                  barw*0.9,
                                                  barh))),
                         QColor(0, 255, 255, 200))


class PlayerWidget(QWidget):
    def __init__(self, player: Player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = player
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.darts_left = 3
        c = self.player.color
        col = 'rgba(%s, %s, %s, 150)' % (c.red(), c.green(), c.blue())
        self.setStyleSheet('PlayerWidget{background-color: %s}' % col)
        tf = QTransform()
        self.darts_left_img = QPixmap('img/dw.png').transformed(tf.rotate(90))
        self.score = ''
        self.dart_board_widget = DartboardWidget(self, mini_version=True)
        self.board_dropdown = QComboBox(self)

        self.board_dropdown.addItem("All Time")
        self.board_dropdown.addItem("Current Leg")
        self.board_dropdown.addItem("Current Set")
        self.board_dropdown.addItem("Current Game")
        self.board_dropdown.currentIndexChanged.connect(self.repaint_dart_board)
        self.won_sets = 0
        self.won_legs = 0
        self.legs_to_set = player.get_current_game().legs_to_set
        self.sets_to_match = player.get_current_game().sets_to_match
        self.show()

    def repaint_dart_board(self):
        text = self.board_dropdown.currentText()
        if text == "Current Leg":
            takes = self.player.get_current_leg_takes()
        elif text == "Current Set":
            takes = self.player.get_current_set_takes()
        elif text == "Current Game":
            takes = self.player.get_current_game_takes()
        else:
            takes = self.player.all_takes.all()
        self.dart_board_widget.set_darts(list(
            itertools.chain.from_iterable([t2.darts for t2 in
                                           [t for t in takes]]
                                          # [t for t in self.player.all_takes.all()]]
                                          )))

    def set_player_score(self, score: int):
        self.score = (str(score))
        self.repaint_dart_board()
        self.darts_left = self.player.get_darts_left()
        self.won_legs = self.player.number_of_won_legs()
        self.won_sets = self.player.number_of_won_sets()
        self.repaint()

    def resizeEvent(self, event: QResizeEvent):
        side = int(min(self.height(), self.width() / 2))
        self.dart_board_widget.setGeometry(0, 0, side, side)

    def setGeometry(self, *__args):
        if isinstance(__args[0], QRect):
            size = __args[0].width(), __args[0].height()
        else:
            size = __args[2], __args[3]
        self.setMinimumSize(*size)
        self.resize(*size)
        super().setGeometry(*__args)

    def paintEvent(self, event: QPaintEvent):
        side = int(min(self.height(), self.width() / 2))
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        # DARTS-LEFT-ICONS
        for i in range(1, self.darts_left + 1):
            painter.drawPixmap(QRect(2 * side * (12/13), (5 + side) * ((i)/13),
                                     side * (1/8),
                                     side/12),
                               self.darts_left_img)
        # painter.save()

        # painter.setFont(self.wire_font)

        # PLAYER NAME
        painter_helper.draw_text(self, painter, QFont('Calibri'), self.player.name, Qt.white,
                                 QRectF(side, 0, self.width() - side, self.height() / 5))
        # SCORE
        painter_helper.draw_text(self, painter, QFont('Calibri'), self.score, Qt.white,
                                 QRectF(side*1.1, self.height() * (2 / 3), self.width() - side, self.height() / 3),
                                 align=Qt.AlignLeft)
        # LEGS
        painter_helper.draw_text(self, painter, QFont('Calibri'), 'L: %s' % self.won_legs, Qt.white,
                                 QRectF(side*1.1, self.height() * (1.05 / 3), self.width() - side, self.height() / 8),
                                 align=Qt.AlignLeft)
        painter.fillRect(QRect(*(int(v) for v in (side*1.1, self.height() * (1.5 / 3), (self.width()-(1.2*side)),
                                                  self.height()/25))),
                         QColor(25, 25, 25, 100))
        painter.fillRect(QRect(side*1.11, self.height() * (1.53 / 3), (self.width()-(1.23*side)) * (self.won_legs/self.legs_to_set),
                               self.height()/50), QColor(0, 255, 255, 200))

        # SETS
        painter_helper.draw_text(self, painter, QFont('Calibri'), 'S: %s' % self.won_sets, Qt.white,
                                 QRectF(side*1.1, self.height() * (1.65 / 3), self.width() - side, self.height() / 8),
                                 align=Qt.AlignLeft)
        painter.fillRect(QRect(*(int(v) for v in (side * 1.1, self.height() * (2.1 / 3), (self.width() - (1.2 * side)),
                                                  self.height() / 25))),
                         QColor(25, 25, 25, 100))
        painter.fillRect(QRect(side * 1.11, self.height() * (2.13 / 3),
                               (self.width() - (1.23 * side)) * (self.won_sets / self.sets_to_match),
                               self.height() / 50), QColor(0, 255, 255, 200))

        # painter.restore()
        event.accept()

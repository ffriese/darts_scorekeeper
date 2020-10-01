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
    def __init__(self, parent: "PlayerWidget", *args, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.total_sets = 1
        self.total_legs = 1
        self.sets = 0
        self.legs = 0
        self.darts = 0
        self.player_widget = parent

    def paintEvent(self, event: QPaintEvent):

        self.total_legs = self.player_widget.legs_to_set
        self.total_sets = self.player_widget.sets_to_match
        self.legs = self.player_widget.won_legs
        self.sets = self.player_widget.won_sets
        painter = QPainter()
        painter.begin(self)
        margin = 5
        inner_margin = 3
        barw = ((self.width() - margin)/2)-(inner_margin*2)
        barh = (self.height()* (2/3)-(inner_margin*2))

        # LEGS

        painter_helper.draw_text2(painter, QFont('Calibri'), 'Legs: %s' % self.legs, Qt.white,
                                 QRectF(0, 0, self.width(), self.height()))#,
                                 #align=Qt.AlignRight, angle=5)
        painter.fillRect(QRect(*(int(v) for v in (0,
                                                  self.height()*(1/3),
                                                  barw+inner_margin*2,
                                                  barh+inner_margin*2))),
                         QColor(25, 25, 25, 100))
        leg_h = barh*(self.legs/self.total_legs)
        painter.fillRect(QRect(*(int(v) for v in (inner_margin,
                                                  self.height()*(1/3)+inner_margin+barh-leg_h,
                                                  barw,
                                                  leg_h))),
                         QColor(0, 255, 255, 200))
        # SETS
        painter.fillRect(QRect(*(int(v) for v in (margin+barw+inner_margin*2,
                                                  self.height()*(1/3),
                                                  barw+inner_margin*2,
                                                  barh+inner_margin*2))),
                         QColor(25, 25, 25, 100))
        set_h = barh*(self.sets/self.total_sets)
        painter.fillRect(QRect(*(int(v) for v in (margin+barw+inner_margin*3,
                                                  self.height()*(1/3)+inner_margin+barh-set_h,
                                                  barw,
                                                  set_h))),
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


        self.progress_widget = MatchProgressWidget(self)
        self.progress_widget.setGeometry(50, 50, 100, 100)
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

        self.progress_widget.setGeometry(self.width()-side*(1/5), 0, side*(1/5), self.height()*(2/3))

    def setGeometry(self, *__args):
        if isinstance(__args[0], QRect):
            size = __args[0].width(), __args[0].height()
        else:
            size = __args[2], __args[3]
        self.setMinimumSize(*size)
        self.resize(*size)
        super().setGeometry(*__args)

    def paintEvent(self, event: QPaintEvent):
        side = min(self.height(), int(self.width() / 2))
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
        h = min(side*(2/3), self.height()/2)
        painter_helper.draw_text(self, painter, QFont('Calibri'), self.score, Qt.white,
                                 QRectF(side, self.height()-h, self.width() - side, h),
                                 align=Qt.AlignRight)

        event.accept()

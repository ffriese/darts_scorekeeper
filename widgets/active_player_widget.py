from PyQt5.QtCore import QPointF, Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPaintEvent, QPolygon, QBrush, QFont
from PyQt5.QtWidgets import QWidget

from models.objects.player import Player
from models.objects.take import Take
from widgets import painter_helper


class ActivePlayerWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = None
        self.score = None
        self.color = QColor(10, 10, 10, 150)
        self.take = None
        self.show()

    def set_player(self, player: Player = None, score: int = None):
        self.player = player
        self.score = score
        if player is None:
            self.color = QColor(10, 10, 10, 150)
            self.take = None
        else:
            self.color = player.color
        self.color.setAlpha(150)
        self.repaint()

    def set_take(self, take: Take):
        self.take = take
        self.repaint()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(self.color)
        painter.setBrush(QBrush(self.color))
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p1 = (self.width(), self.height())
        p2 = (self.width() * 0.75, self.height())
        p3 = (self.width() * 0.95, 0)
        p4 = (self.width(), 0)

        p5 = (0, self.height())
        p6 = (self.width() * 0.5, self.height())
        p7 = (self.width() * 0.27, 0)
        p8 = (0, 0)
        painter.drawConvexPolygon(QPolygon([QPointF(*p).toPoint() for p in [p1, p2, p3, p4]]))

        if self.player is not None:
            painter_helper.draw_text(self, painter, QFont('Calibri'), self.player.name, Qt.white,
                                     QRectF(self.width() * 0.8, self.height() / 2.8,
                                            self.width() * 0.20, self.height() / 8),
                                     Qt.AlignRight)
            painter_helper.draw_text(self, painter, QFont('Calibri'), str(self.score), Qt.white,
                                     QRectF(self.width()*0.7, self.height()/2, self.width()*0.3, self.height()/2),
                                     Qt.AlignRight)

        if self.take is not None and self.take.player is not None:
            take_color = self.take.player.color
            take_color.setAlpha(150)
        else:
            take_color = QColor(10, 10, 10, 50)
        painter.setPen(take_color)
        painter.setBrush(QBrush(take_color))
        painter.drawConvexPolygon(QPolygon([QPointF(*p).toPoint() for p in [p5, p6, p7, p8]]))

        if self.take is not None:
            for i, dart in enumerate(self.take.darts):
                painter_helper.draw_text(self, painter, QFont('Calibri'), dart.get_field_string(), Qt.white,
                                         QRectF(0, i*(self.height() / 3)+(self.height()/24), self.width() * 0.25,
                                                self.height() / 4),
                                         Qt.AlignLeft)
            painter_helper.draw_text(self, painter, QFont('Calibri'), str(self.take.get_score()), Qt.white,
                                     QRectF(self.width()*(1/3), self.height()*(2/3), self.width()*(1/3), self.height()*(1/3)))
        event.accept()

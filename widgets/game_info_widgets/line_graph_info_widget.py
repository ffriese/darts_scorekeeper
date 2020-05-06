from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPaintEvent, QPainter, QColor, QBrush
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class LineGraphInfoWidget(GameInfoWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total = None
        self.scale = 1


    def draw_mark(self, painter, points: int):
        mark_x = 2
        mark_y = 5 + (self.total-points)*self.scale
        painter.drawLine(mark_x, mark_y, self.width()/20, mark_y)
        painter.drawText(mark_x, mark_y, str(points))

    def draw_dot(self, painter, x, y, color, connect=None):
        painter.setPen(color)
        painter.setBrush(QBrush(color))
        if connect is not None:
            painter.drawLine(QPoint(x, y), connect)
        painter.drawEllipse(QPoint(x, y), 5, 5)

    def draw_y_axis(self, painter):
        self.scale = (self.height()-10) / self.total
        painter.setPen(QColor(255, 255, 255))
        painter.drawLine(15, 5, 15, self.height()-5)
        for p in [i * 100 for i in range(int(self.total / 100) + 1)]:
            self.draw_mark(painter, p)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.draw_y_axis(painter)
        self.draw_dotted_lines(painter)

        event.accept()

    def draw_dotted_lines(self, painter):
        raise NotImplementedError()
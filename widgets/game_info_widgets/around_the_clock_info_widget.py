from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPainter, QColor

from widgets.game_info_widgets.line_graph_info_widget import LineGraphInfoWidget


class AroundTheClockInfoWidget(LineGraphInfoWidget):
    def __init__(self, game: "AroundTheClock", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.total = 21

    def draw_y_axis(self, painter):
        self.scale = (self.height()-10) / self.total
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.setPen(QColor(255, 255, 255))
        painter.drawLine(15, 5, 15, self.height()-5)
        for p in range(1, 21):
            self.draw_mark(painter, p)

    def draw_dotted_lines(self, painter):

        if self.players:
            max_takes = max([len(p.get_current_leg_takes()) for p in self.players])
            if max_takes > 0:
                step_size = (self.width() - 35) / max_takes
            else:
                step_size = 0
            for player in self.players:
                score = 1
                _x, _y = 15, 21 * self.scale
                for i, take in enumerate(player.get_current_leg_takes()):
                    for dart in take.darts:
                        if dart.get_segment().sector == score:
                            score += 1
                    x = 15 + step_size + i * step_size
                    y = (self.total-score) * self.scale
                    self.draw_dot(painter, x, y, player.color, connect=QPoint(_x, _y))
                    _x = x
                    _y = y

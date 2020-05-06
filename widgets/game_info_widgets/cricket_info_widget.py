import math

from PyQt5.QtCore import QPoint, QRect, Qt, QRectF
from PyQt5.QtGui import QPaintEvent, QPainter, QColor, QBrush, QFont, QPen

from widgets import painter_helper
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class CricketInfoWidget(GameInfoWidget):
    def __init__(self, game: "Cricket", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.total = 100
        self.scale = 1

    def point_on_circle(self, center, radius, angle):
        x = center[0] + (radius * math.cos(angle))
        y = center[1] + (radius * math.sin(angle))

        return x, y

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        if self.players:
            sector_width = self.height()*0.1
            player_height = self.height()*0.05
            player_width = (self.width()-sector_width)/len(self.players)
            sector_height = (self.height()-player_height) / len(self.game.goal_segments)
            circle_diam = min(player_width*0.3, sector_height*0.3)
            for i, gs in enumerate(self.game.goal_segments):
                rect = QRect(0, player_height + i * sector_height, sector_width, sector_height)
                # painter.fillRect(rect,
                #                  QColor(100, 100, 100, 100))
                painter_helper.draw_text(self, painter, QFont('Calibri'), str(gs) if gs != 25 else 'B', Qt.white,
                                         QRectF(rect.adjusted(sector_width*0.2, sector_height*0.35,
                                                              -sector_width*0.4, - sector_height*0.4)))
            for i, player in enumerate(self.players):
                color = player.color
                color.setAlpha(180)
                rect = QRect(sector_width + i * player_width, 0, player_width, player_height)
                painter.fillRect(rect, color)

                painter_helper.draw_text(self, painter, QFont('Calibri'), player.name[0], Qt.white,
                                         QRectF(rect.adjusted(player_width*0.1, player_height*0.1,
                                                              -player_width*0.1, - player_height*0.1)))
                if self.game.get_current_player() == player:
                    color = player.color
                    color.setAlpha(255)
                    painter.setPen(QPen(color, circle_diam/10))
                else:
                    painter.setPen(QPen(QColor(255, 255, 255), circle_diam/10))
                for j, gs in enumerate(self.game.goal_segments):
                    c_center = (sector_width + i * player_width + circle_diam/2,
                                player_height + j * sector_height + sector_height/2)
                    num = self.game.sector_hits[gs][player]
                    if num > 0:
                        painter.drawLine(QPoint(*self.point_on_circle(c_center, circle_diam/2, 45)),
                                         QPoint(*self.point_on_circle(c_center, circle_diam/2, 180)))
                    if num > 1:
                        painter.drawLine(QPoint(*self.point_on_circle(c_center, circle_diam/2, -45)),
                                         QPoint(*self.point_on_circle(c_center, circle_diam/2, -180)))
                    if num > 2:
                        painter.drawEllipse(sector_width + i * player_width,
                                            player_height + j * sector_height + sector_height/2 - circle_diam/2,
                                            circle_diam, circle_diam)
                    if num > 3:
                        rows = (num+1.5) // 5
                        offset = 0#(sector_height/2 - circle_diam/2) / rows
                        for k in range(0, num-3):
                            row = (k // 5)+1
                            x1 = sector_width + i * player_width + circle_diam + ((k % 5)+1) * (sector_width / 10)
                            y = player_height + j * sector_height + offset \
                                + row * ((sector_height-circle_diam)/2) / rows

                            if (k+1) % 5 == 0:
                                x1 = sector_width + i * player_width + circle_diam + 0.4*(sector_width / 10)
                                x2 = sector_width + i * player_width + circle_diam + 4.4*(sector_width / 10)
                            else:
                                x2 = x1
                            painter.drawLine(QPoint(x1,
                                                    y),
                                             QPoint(x2,
                                                    y + row*circle_diam/rows)
                                             )


        event.accept()

import math
import time
from math import floor
from typing import List, Union

import numpy as np
from PyQt5.QtCore import Qt, QPointF, QPoint, QRectF, pyqtSignal, QSize
from PyQt5.QtGui import QFontDatabase, QFont, QColor, QPainter, QBrush, QPen, QPainterPath, QImage, QMouseEvent, \
    QPaintEvent, QPixmap, QResizeEvent, QKeyEvent
from PyQt5.QtWidgets import QWidget

from constants import *
from logic.helper import MathHelper
from logic.settings import Settings
from models.dartboard import DartBoard, Bed
from models.objects.dart import Dart


class DartWidget(QWidget):
    __DART_IMAGE__ = QImage("img/hit.png")

    class DragWidget(QWidget):
        __ORIG_MASK_PATH__ = "img/hit_ns_white.png"
        __ORIG_MASK__ = None  # type: QPixmap
        __MASK__ = None  # type: QPixmap

        def __init__(self, parent, *args, **kwargs):
            if DartWidget.DragWidget.__ORIG_MASK__ is None:
                DartWidget.DragWidget.__ORIG_MASK__ = QPixmap(DartWidget.DragWidget.__ORIG_MASK_PATH__)
            super().__init__(*args, parent=parent, **kwargs)
            self.parent = parent
            self.drag_mode = False
            self.setMouseTracking(True)
            # Settings.DRAG_DARTS_ENABLED.register_change_handler(self.setDragCursor)
            self.HIGHLIGHT = False

        # def setDragCursor(self, value):
        #     if value:
        #         self.setCursor(Qt.DragMoveCursor)
        #     else:
        #         self.setCursor(Qt.CrossCursor)

        def paintEvent(self, event: QPaintEvent):
            painter = QPainter(self)
            if self.parent.dart is not None:
                painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
                if Settings.DRAG_DARTS_ENABLED.get() and self.HIGHLIGHT:
                    painter.drawImage(QRectF(0, 0, self.width(), self.height()), self.__MASK__)
                # painter.fillRect(QRectF(0, 0, self.width(), self.height()), QColor(255, 0, 0, 255))

        def mouseMoveEvent(self, event: QMouseEvent):
            if self.drag_mode:
                p = self.mapTo(self.parent.parent(), QPoint(event.x(), event.y()))
                self.parent.dart.hit_location = self.parent.parent().mouse_coords_to_board_coords(
                    p.x(), p.y())
                self.parent.parent().repaint()
                event.accept()
            else:
                local = QPoint(event.x(), event.y())
                event.ignore()
                self.parent.parent().propagate_mouse_over(self.mapToGlobal(local))

        def is_under_mouse(self, local):
            val = -1 < local.x() <= self.width() and -1 < local.y() <= self.height() \
                   and self.__MASK__.pixel(local.x(), local.y()) != 0
            self.HIGHLIGHT = val
            self.repaint()
            return val

        def mousePressEvent(self, event: QMouseEvent):
            if self.is_under_mouse(QPoint(event.x(), event.y())) and Settings.DRAG_DARTS_ENABLED.get():
                self.drag_mode = True
                print('pressed')
                event.accept()
            else:
                print('PRESS NEEDS SEND_THROUGH')
                # self.parent.parent().mousePressEvent(event)
                local = QPoint(event.x(), event.y())
                self.parent.parent().propagate_mouse_press(self.mapToGlobal(local), self)
                event.ignore()

        def mouse_press(self, local) -> bool:
            if self.is_under_mouse(local) and Settings.DRAG_DARTS_ENABLED.get():
                self.drag_mode = True
                self.grabMouse()
                print(self.parent.dart, 'grabbed the mouse!')
                return True
            return False

        def mouseReleaseEvent(self, event: QMouseEvent):
            if Settings.DRAG_DARTS_ENABLED.get() or self.drag_mode:
                self.drag_mode = False
                print('released')
                self.parent.parent().updated_dart.emit(self.parent.dart)
                event.accept()
                self.releaseMouse()
            else:
                print('RELEASE NEEDS SEND_THROUGH')
                # self.parent.parent().mouseReleaseEvent(event)
                event.ignore()

    def __init__(self, dart: Union[Dart, None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dart = dart
        self.drag_widget = DartWidget.DragWidget(parent=self)
        self.drag_widget.setGeometry(0, 0, self.width(), self.height())

    def paintEvent(self, event: QPaintEvent):
        if self.dart is not None:
            painter = QPainter(self)
            painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            painter.drawImage(QRectF(0, 0, self.width(), self.height()), self.__DART_IMAGE__)

    def resizeEvent(self, event: QResizeEvent):
        self.drag_widget.setGeometry(0, 0, self.width(), self.height())
        self.drag_widget.__MASK__ = self.drag_widget.__ORIG_MASK__.scaled(event.size()).toImage()


class DartboardWidget(QWidget):

    clicked_dart = pyqtSignal(QPointF)
    updated_dart = pyqtSignal(Dart)

    def __init__(self, parent=None, mini_version=False):
        super(DartboardWidget, self).__init__(parent=parent)
        self.mini_version = mini_version
        if not mini_version:
            # self.setMouseTracking(True)
            self.setCursor(Qt.CrossCursor)
            self.dot_width = 1.8
            self.dot_pen_color = QColor(0, 255, 155)
            self.dot_target_color = QColor(255, 0, 0)
            self.dot_hit_color = QColor(0, 0, 255)
        else:
            self.dot_pen_color = QColor(255, 255, 255)
            self.dot_hit_color = self.dot_pen_color
            self.dot_target_color = self.dot_pen_color
            self.dot_width = 2
            self.heat_map = None  # type: QImage
            self.heat_map_darts = None
        font_id = QFontDatabase().addApplicationFont('fonts/WireOne.ttf')
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            family = 'Arial'

        self.green = QColor(0, 131, 73)
        self.red = QColor(186, 21, 50)

        self.wire_font = QFont(family, 20)
        self.paths = DartBoard.get_segment_areas()

        self.background_cache = None

        self.current_darts = []
        self._dart_widgets = [DartWidget(None, parent=self) for _ in range(3)] if not self.mini_version else []
        self.dart_widgets = {}  # type: Dict[Dart, DartWidget]
        self.scale = None
        if not self.mini_version:
            Settings.DISPLAY_DARTS.register_change_handler(self.repaint, pass_value=False)
            Settings.DRAG_DARTS_ENABLED.register_change_handler(self.unset_cursor)

    def set_darts(self, darts: List[Dart]):
        self.current_darts = darts
        # TODO: fit number of available darts to max(len(darts), 3)
        if not self.mini_version:
            self.dart_widgets = {}
            for dw in self._dart_widgets:
                dw.dart = None
            for i, dart in enumerate(self.current_darts):
                self.dart_widgets[dart] = self._dart_widgets[i]
                self.dart_widgets[dart].dart = dart

        self.repaint()

    def propagate_mouse_over(self, _global):
        cursor = Qt.CrossCursor
        for dw in self.dart_widgets.values():
            loc = dw.drag_widget.mapFromGlobal(_global)
            if dw.drag_widget.is_under_mouse(loc) and Settings.DRAG_DARTS_ENABLED.get():
                cursor = Qt.DragMoveCursor
                break
        self.setCursor(cursor)

    def unset_cursor(self, value):
        if not value:
            for dw in self.dart_widgets.values():
                dw.drag_widget.HIGHLIGHT = False
                dw.drag_widget.repaint()
            self.setCursor(Qt.CrossCursor)

    def propagate_mouse_press(self, _global, sender):
        for dw in self.dart_widgets.values():
            loc = dw.drag_widget.mapFromGlobal(_global)
            if dw.drag_widget.mouse_press(loc):
                return

    def mouse_coords_to_board_coords(self, x, y) -> QPointF:
        x /= self.scale
        y /= self.scale
        return QPointF(x-OFFSET_FROM_ORIGIN_MM, y-OFFSET_FROM_ORIGIN_MM)

    #############
    # OVERRIDES #
    #############
    # def mouseMoveEvent(self, event: QMouseEvent):
    #     for dw in self.dart_widgets.values():
    #         if dw.underPoint(QPoint(event.x(), event.y())):
    #             print(dw)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.clicked_dart.emit(self.mouse_coords_to_board_coords(event.x(), event.y()))
        event.accept()

    def draw_heatmap(self):
        from logic.helper import TimerObject
        scale = 1  # self.scale
        side = int(2*(RADIUS_OUTER_DOUBLE_MM+OFFSET_FROM_ORIGIN_MM))
        timer = TimerObject()
        histogram = np.zeros(
            #(self.width(), self.height()),
            (side, side),
            np.float32)
        self.heat_map_darts = self.current_darts.copy()
        timer.finished('initialization')
        def gen_kernel(k, s):
            # generate a (2k+1)x(2k+1) gaussian kernel with mean=0 and sigma = s
            k = int(k)
            s = max(int(s), 1)
            probs = [np.exp(-z * z / (2 * s * s)) / np.sqrt(2 * np.pi * s * s) for z in range(-k, k + 1)]
            return np.outer(probs, probs) * 20
        size = 8
        kernel = gen_kernel(5*size*scale, size*scale)

        timer.finished('generate kernel')
        k0 = int(kernel.shape[0])
        k0h = int(math.floor(k0 / 2))
        k0h1 = k0 - k0h
        k1 = int(kernel.shape[1])
        k1h = int(math.floor(k1 / 2))
        k1h1 = k1 - k1h
        if self.heat_map_darts:
            for dart in self.heat_map_darts:
                result = dart.hit_location
                c = int((OFFSET_FROM_ORIGIN_MM+result.x())*scale)
                r = int((OFFSET_FROM_ORIGIN_MM+result.y())*scale)

                if min([r - k0h,  c - k1h]) >= 0 and \
                    max([r + k0h1,  c + k1h1]) <= side:
                    # print([r, kernel.shape[0], c, kernel.shape[1], histogram.shape])
                    # histogram[r, c] += 1
                    # continue
                    histogram[r-k0h:r + k0h1, c-k1h:c + k1h1] += kernel

        timer.finished('sum histogram')
        print('got histogram')
        histogram /= np.max(histogram) / 255.0
        histogram = histogram.astype(np.uint8)
        height, width = histogram.shape

        timer.finished('prepare for colorization')
        #rgb = (np.array(MathHelper.vectorized_hsl_to_rgb(histogram/255))*255).astype(np.uint8)

        #timer.finished('colorize')
        rgb = (np.array(MathHelper.vectorized_hsl_to_rgb2(histogram/255))*255).astype(np.uint8)

        timer.finished('colorize2')
        histogramrgb = np.stack((
            #histogram, histogram, histogram,
                                rgb[0], rgb[1], rgb[2],
                                 #np.where(histogram != 0.0, 255, 0).astype(np.uint8)),
                                #np.ones(histogram.shape, dtype=np.uint8)*255),
                                histogram),
                                axis=-1)

        timer.finished('stack channels')
        #histogramrgb = np.stack((histogram,) *4, axis=-1)
        # print(np.max(histogramrgb[:, :, 0]), np.max(histogramrgb[:, :, 1]), np.max(histogramrgb[:, :, 2]),
        #       np.max(histogramrgb[:, :, 3]), np.median(histogramrgb[:, :, 3]))
        # print(histogramrgb.shape)

        bytesPerLine = height
        # qImg = QImage(histogram.data, width, height, bytesPerLine, QImage.Format_Alpha8)
        qImg2 = QImage(histogramrgb.data, width, height, bytesPerLine*4, QImage.Format_RGBA8888)
        timer.finished('convert to qimage')
        timer.get_report()
        return qImg2
        # painter.setBrush(QBrush(self.dot_hit_color))
        # painter.drawEllipse(result + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM),
        #                     self.dot_width, self.dot_width)


    def paintEvent(self, event: QPaintEvent):
        black_bg = QColor(10, 10, 10)  # (10/255, 10/255, 10/255)
        self.scale = float(self.width()) / ((RADIUS_OUTER_DOUBLE_MM + OFFSET_FROM_ORIGIN_MM) * 2.0)

        off = OFFSET_FROM_ORIGIN_MM
        center = QPointF(RADIUS_OUTER_DOUBLE_MM, RADIUS_OUTER_DOUBLE_MM)
        offset = QPoint(off, off)

        if self.background_cache is None or self.size() != self.background_cache.size():
            # print('%s redraw-bg' % time.time())
            self.background_cache = QPixmap(self.size())
            self.background_cache.fill(Qt.transparent)
            painter = QPainter(self.background_cache)
            painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            painter.scale(self.scale, self.scale)
            # DRAW BLACK BOARD BACKGROUND

            # SHADOW
            if not self.mini_version:
                painter.save()
                painter.setBrush(QBrush(QColor(20, 20, 20, 100)))
                painter.setPen(QColor(20, 20, 20, 0))
                painter.drawEllipse(center + offset + QPointF(6, 7), RADIUS_OUTER_DOUBLE_MM * 1.22,
                                    RADIUS_OUTER_DOUBLE_MM * 1.22)
                painter.restore()

            painter.save()
            painter.setBrush(QBrush(black_bg))
            painter.drawEllipse(center + offset, RADIUS_OUTER_DOUBLE_MM * 1.22, RADIUS_OUTER_DOUBLE_MM * 1.22)
            painter.restore()

            # DRAW WIRE-RING (WITHOUT NUMBERS)
            if not self.mini_version:
                painter.setPen(QColor(255, 255, 255))
                painter.drawEllipse(center + offset, RADIUS_OUTER_DOUBLE_MM * 1.188, RADIUS_OUTER_DOUBLE_MM * 1.188)

            pen = QPen(QColor(200, 200, 200))

            keys = list(self.paths.keys())

            for i in range(len(keys)):
                segment = keys[i]

                sector_index = SECTOR_ORDER.index(segment.sector) if segment.sector in SECTOR_ORDER else 25
                bed = segment.bed

                if sector_index == 25:  # BULLS EYE
                    color = self.red
                    single_color = self.green
                elif sector_index % 2 == 0:
                    color = self.red
                    single_color = black_bg
                else:
                    color = self.green
                    single_color = QColor(225, 208, 182)
                if bed in [Bed.SINGLE, Bed.INNER_SINGLE, Bed.OUTER_SINGLE]:
                    color = single_color
                elif bed == Bed.TRIPLE:

                    # DRAW NUMBERS
                    triple_center = self.paths[segment].boundingRect().center()
                    text_pos = triple_center - center

                    new_font = True

                    if new_font:  # NEW FONT
                        if sector_index < 6 or sector_index > 14:
                            text_pos *= 1.85
                        else:
                            text_pos *= 1.93

                    else:  # OLD FONT
                        text_pos *= 1.9

                    text_pos += center + offset
                    painter.save()
                    painter.translate(text_pos.x(), text_pos.y())
                    angle = math.atan2(center.y() + off - text_pos.y(), center.x() + off - text_pos.x())
                    angle = angle * 180 / math.pi  # convert to degrees
                    up = -90

                    if angle < -1:  # 11 and 6 are still drawn normally, everything below flips
                        up += 180
                    painter.rotate(angle + up)
                    painter.setFont(self.wire_font)
                    painter.setPen(Qt.white)

                    painter.setRenderHints(
                        QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)

                    if new_font:  # NEW FONT
                        text_path = QPainterPath()

                        x0 = -off / 6 if angle < -1 else -off / 6
                        y0 = off / 6 if angle < -1 else off / 6

                        text_path.addText(x0, y0, self.wire_font, str(segment.sector))
                        painter.drawPath(text_path)

                    else:  # OLD FONT
                        painter.drawText(-off / 2, -off / 2, off, off, Qt.AlignCenter | Qt.AlignHCenter, str(segment[0]))

                    painter.restore()
                    # break

                painter.fillPath((self.paths[segment].translated(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM)),
                                 QBrush(color))

            # DRAW WIRE
            if floor(self.scale) > 0:
                pen.setWidthF(self.scale / 2.0)
                painter.setPen(pen)

                keys = list(self.paths.keys())
                for i in range(len(keys)):
                    segment = keys[i]
                    if segment.sector < 25:  # BULL'S EYE WIRE IS DRAWN AS A CIRCLE LATER ON
                        painter.drawPath(self.paths[segment].translated(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM))

            if self.mini_version:
                painter.setPen(QColor(80, 80, 80, 200))
                painter.setBrush(QBrush(QColor(80, 80, 80, 200)))
                painter.drawEllipse(center + offset, RADIUS_OUTER_DOUBLE_MM * 1.22, RADIUS_OUTER_DOUBLE_MM * 1.22)

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.width(), self.height(), self.background_cache)

        painter.scale(self.scale, self.scale)
        if self.mini_version:
            # or self.heat_map.size() != self.size() \
            if self.heat_map is None  \
                    or self.current_darts != self.heat_map_darts:
                self.heat_map = self.draw_heatmap()
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawImage(QRectF(0, 0, self.heat_map.width(), self.heat_map.height()), self.heat_map)


        # DRAW THROWS
        painter.setPen(QPen(self.dot_pen_color))

        if not self.mini_version and self.current_darts:
            for dart in self.current_darts:
                target = dart.target_location
                result = dart.hit_location
                if target.isNull():
                    painter.setBrush(QBrush(self.dot_hit_color))
                    painter.drawEllipse(result + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM),
                                        self.dot_width, self.dot_width)
                else:
                    painter.setBrush(QBrush(self.dot_target_color))
                    painter.drawEllipse(target + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM),
                                        self.dot_width, self.dot_width)
                    painter.setBrush(QBrush(self.dot_hit_color))
                    painter.drawEllipse(result + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM),
                                        self.dot_width, self.dot_width)
                    painter.drawLine(target + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM),
                                     result + QPointF(OFFSET_FROM_ORIGIN_MM, OFFSET_FROM_ORIGIN_MM))

                if not self.mini_version:
                    if Settings.DISPLAY_DARTS.get():
                        self.dart_widgets[dart].setVisible(True)
                        self.dart_widgets[dart].resize(QSize(*(v * self.scale for v in
                                                              (
                                                               267.0 / 2.5,
                                                               307.0 / 2.5))))
                        self.dart_widgets[dart].move(*(v * self.scale for v in
                                                              (result.x() + OFFSET_FROM_ORIGIN_MM - (55.0 / 2.5),
                                                               result.y() + OFFSET_FROM_ORIGIN_MM - (72.0 / 2.5)
                                                               )))
                        # self.dart_widgets[dart].setGeometry(*(v * self.scale for v in
                        #                                       (result.x() + OFFSET_FROM_ORIGIN_MM - (55.0 / 2.5),
                        #                                        result.y() + OFFSET_FROM_ORIGIN_MM - (72.0 / 2.5),
                        #                                        267.0 / 2.5,
                        #                                        307.0 / 2.5)))

                        #self.dart_widgets[dart].set_mask(QPixmap("img/hit.png").scaled(QSize(self.scale*267/2.5, self.scale*307/2.5)).mask())
                        # self.dart_widgets[dart].update()
                        # self.dart_widgets[dart].repaint()
                        # painter.drawImage(QRectF(result.x() + OFFSET_FROM_ORIGIN_MM - (55.0 / 2.5),
                        #                          result.y() + OFFSET_FROM_ORIGIN_MM - (72.0 / 2.5),
                        #                          267.0 / 2.5,
                        #                          307.0 / 2.5),
                        #                   QImage("img/hit.png"))
                    else:
                        self.dart_widgets[dart].setVisible(False)
        # event.accept()

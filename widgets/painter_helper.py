from PyQt5.QtCore import QRect, Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QTextOption, QFontMetrics


def draw_text(self, painter: QPainter, font: QFont, text: str, color: QColor, rect: QRectF, align: Qt.Alignment= Qt.AlignLeft, angle=0.0):
    # painter.setPen(Qt.red)
    # painter.setBrush(QBrush(Qt.red))
    # painter.fillRect(rect, Qt.red)
    painter.save()
    painter.rotate(angle)
    painter.setPen(color)
    painter.setBrush(QBrush(color))
    font.setPixelSize(rect.height())
    #font.setStyleHint(QFont.Times, QFont.PreferAntialias)
    painter.setFont(font)
    painter.setRenderHints(
        QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
    option = QTextOption()
    option.setAlignment(align)

    # fontMetrics = QFontMetrics(font)
    # fontMetrics.boundingRect(text)

    painter.drawText(rect, text, option)
    painter.restore()

def draw_text2(painter: QPainter, font: QFont, text: str, color: QColor, rect: QRectF, align: Qt.Alignment= Qt.AlignLeft, angle=0.0):
    painter.save()
    painter.setFont(font)
    fm=QFontMetrics(painter.font())
    sx = rect.width() * 1.0 / fm.width(text)
    sy = rect.height() * 1.0 / fm.height()
    painter.setPen(color)
    painter.setBrush(QBrush(color))
    painter.translate(rect.center())
    sc = min(sx, sy)
    painter.scale(sc, sc)
    painter.translate(-rect.center())
    option = QTextOption()
    option.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
    painter.drawText(rect, text, option)
    painter.restore()
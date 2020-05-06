from PyQt5.QtCore import QRect, Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QTextOption, QFontMetrics


def draw_text(self, painter: QPainter, font: QFont, text: str, color: QColor, rect: QRectF, align: Qt.Alignment= Qt.AlignLeft):
    # painter.setPen(Qt.red)
    # painter.setBrush(QBrush(Qt.red))
    # painter.fillRect(rect, Qt.red)
    painter.save()
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
from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget


class GameInfoWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setStyleSheet('GameInfoWidget{background-color: rgba(10,10,10,190)}')
        self.players = []
        self.setVisible(True)

    def update_players(self, players: List["Player"]):
        self.players = players
        self.repaint()

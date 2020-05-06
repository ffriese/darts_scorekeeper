from PyQt5.QtCore import QPoint

from widgets.game_info_widgets.line_graph_info_widget import LineGraphInfoWidget


class X01InfoWidget(LineGraphInfoWidget):
    def __init__(self, game: "X01", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.total = game.target_score

    def draw_dotted_lines(self, painter):

        if self.players:
            max_takes = max([len(p.get_current_leg_takes()) for p in self.players])
            if max_takes > 0:
                step_size = (self.width() - 35) / max_takes
            else:
                step_size = 0
            for player in self.players:
                score = self.total
                _x, _y = 15, 0
                for i, take in enumerate(player.get_current_leg_takes()):
                    score -= take.get_score()
                    x = 15 + step_size + i * step_size
                    y = (self.total - score) * self.scale
                    self.draw_dot(painter, x, y, player.color, connect=QPoint(_x, _y))
                    _x = x
                    _y = y

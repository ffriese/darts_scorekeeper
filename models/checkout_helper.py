import time
from termcolor import colored
from constants import SECTOR_ORDER
from models.dartboard import DartBoard, Segment, Bed


class CheckoutOption:
    def __init__(self, score: int, segment: Segment, add_neighbors=True, multiplier=1.0):
        self.score = score
        self.segment = segment
        self.bust_risk = 0.0
        self.win_chance = 0.0
        self.neighbors = []

        if segment.score() == self.score:
            self.win_chance += {Bed.SINGLE: 1.0, Bed.TRIPLE: 0.2, Bed.DOUBLE: 0.3}[segment.bed] * multiplier
        elif segment.score() > score:
            self.bust_risk += {Bed.SINGLE: 1.0, Bed.TRIPLE: 0.2, Bed.DOUBLE: 0.3}[segment.bed] * multiplier

        if add_neighbors:
            for bed in [Bed.SINGLE, Bed.DOUBLE, Bed.TRIPLE]:
                if segment.bed != bed:
                    self.neighbors.append(CheckoutOption(score, Segment(segment.sector, bed), False, multiplier=0.6))
            for nb in CheckoutHelper().get_neighbors(self.segment.sector):
                for bed in [Bed.SINGLE, Bed.DOUBLE, Bed.TRIPLE]:
                    self.neighbors.append(CheckoutOption(score, Segment(nb, bed), False, multiplier=0.4))

    def _win_chance(self):
        chance = self.win_chance + sum(n.win_chance for n in self.neighbors)
        if self.score == self.segment.score():
            chance += 0.5
        return chance

    def _bust_risk(self):
        risk = self.bust_risk + sum(n.bust_risk for n in self.neighbors)
        if self.score < self.segment.score():
            risk += 1
        return risk

    def calc_score(self):
        risk = self._bust_risk()
        chance = self._win_chance()
        print('>>> RATING: %.2f' % (chance-risk), self.segment, 'risk:', risk, ', chance:', chance)


def list_options(score):
    print('options for', score)
    options = []
    for num in reversed(range(1, 21)):
        for bed in [Bed.SINGLE, Bed.DOUBLE, Bed.TRIPLE]:
            options.append(CheckoutOption(score, Segment(num, bed)))
    options.append(CheckoutOption(score, Segment(25, Bed.SINGLE)))
    options.append(CheckoutOption(score, Segment(25, Bed.DOUBLE)))
    options.sort(key=lambda x: x._win_chance()-x._bust_risk(), reverse=True)
    for o in options:
        o.calc_score()


class CheckoutHelper():
    def __init__(self):
        pass

    def get_options(self, score, throw=0, way=None):
        print('# call', score, throw, way)
        if score == 0:
            print('='*throw, 'YAY')
            return
        if way is None:
            way = []
        while score != 0 and throw < 3:
            throw += 1
            for num in reversed(range(1, 21)):
                my_way = list(way)
                # triple hit
                if num*3 <= score:
                    # print('>'*throw, 'T%s' % num)
                    time.sleep(1)
                    my_way.append('T%s' % num)
                    self.get_options(score-num*3, throw, my_way)


    def list_outcomes(self, score):

        def print_stuff(score, num):
            def col(_n):
                if _n == 0:
                    return colored(_n, 'green')
                if _n <0:
                    return colored(_n, 'red')
                return _n
            print('   T%s -> %s' % (num, col(score - 3 * num)))
            print('    %s -> %s' % (num, col(score - num)))
        print('FOR FINISHING', score, ':')
        print('')
        for num in reversed(range(1, 21)):
            print('--')
            print_stuff(score, num)
            print('   ---------')
            for n in self.get_neighbors(num):
                print_stuff(score, n)

    def get_neighbors(self, number: int):
        if number in SECTOR_ORDER:
            idx = SECTOR_ORDER.index(number)
            return [SECTOR_ORDER[idx - 1], SECTOR_ORDER[idx + 1 if (idx < len(SECTOR_ORDER) - 1) else 0]]
        else:
            if number == 25:
                return []



if __name__ == '__main__':
    list_options(20)
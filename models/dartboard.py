import math
from collections import defaultdict
from enum import Enum
from typing import Tuple, Union, Dict, List, DefaultDict

import numpy as np
from PyQt5.QtCore import QPointF

from constants import *
from collections import namedtuple
from PyQt5.QtGui import QPainterPath


class Bed(Enum):
    NONE = 0
    SINGLE = 1
    INNER_SINGLE = 2
    OUTER_SINGLE = 3
    DOUBLE = 4
    TRIPLE = 5

    __multipliers__ = {NONE: 0, SINGLE: 1, INNER_SINGLE: 1, OUTER_SINGLE: 1, DOUBLE: 2, TRIPLE: 3}

    def get_multiplier(self):
        return Bed.__multipliers__[self.value]


class Segment(object):
    def __init__(self, sector: int, bed: Bed):
        self.sector = sector
        self.bed = bed

    @staticmethod
    def from_json(json: dict):
        return Segment(json['number'], Bed[json['bed']])

    def to_json(self):
        return {'number': self.sector, 'bed': self.bed.name}

    def score(self):
        return self.sector * self.bed.get_multiplier()

    def __str__(self):
        return '%s %s' % (self.bed.name, self.sector)

    def __eq__(self, other):
        return self.sector == other.sector and self.bed == other.bed

    def __hash__(self):
        return ('%s%s' % (self.sector, self.bed)).__hash__()


def make_partial_pie_part(path, cx, cy, radius1: float, radius2: float, start_angle: float, angle: float):
    s_a = (math.pi / 180.0) * float(start_angle)
    a = (math.pi / 180.0) * float(angle)
    x = float(cx) + (radius1 * math.cos(s_a))
    y = float(cy) - (radius1 * math.sin(s_a))
    path.moveTo(x, y)
    path.arcTo(cx - radius1, cy - radius1, radius1 * 2, radius1 * 2, start_angle, angle)

    x = cx + (radius2 * math.cos(s_a + a))
    y = cy - (radius2 * math.sin(s_a + a))
    path.lineTo(x, y)

    path.arcTo(cx - radius2, cy - radius2, radius2 * 2, radius2 * 2, start_angle + angle, -angle)


class DartBoard(object):
    _instance = None

    @classmethod
    def _get_instance(cls):
        if DartBoard._instance is None:
            DartBoard._instance = DartBoard()
        return DartBoard._instance

    def __init__(self):
        super().__init__()
        self.segment_areas = {}  # type: Dict[Segment, QPainterPath]
        cx = RADIUS_OUTER_DOUBLE_MM
        cy = cx

        sector_angle = 360.0 / 20.0
        start_angle = 90.0 - sector_angle / 2.0  # starting with 20 at the top

        self.available_segments_for_score = defaultdict(list)  # type: defaultdict[int, List[Segment]]

        # BULL'S EYE

        double_bull = QPainterPath()
        make_partial_pie_part(double_bull, cx, cy, 0, RADIUS_INNER_BULL_MM, 0, 360)
        single_bull = QPainterPath()
        make_partial_pie_part(single_bull, cx, cy, RADIUS_INNER_BULL_MM, RADIUS_OUTER_BULL_MM, 0, 360)

        self.segment_areas[Segment(25, Bed.SINGLE)] = single_bull
        self.segment_areas[Segment(25, Bed.DOUBLE)] = double_bull

        self.available_segments_for_score[25].append(Segment(25, Bed.SINGLE))
        self.available_segments_for_score[50].append(Segment(25, Bed.DOUBLE))

        # SEGMENTS FROM 20 TO 1
        angle = start_angle
        for i in range(20):
            inner_single_bed = QPainterPath()
            make_partial_pie_part(inner_single_bed, cx, cy, RADIUS_OUTER_BULL_MM, RADIUS_INNER_TRIPLE_MM, angle,
                                  sector_angle)
            triple_bed = QPainterPath()
            make_partial_pie_part(triple_bed, cx, cy, RADIUS_INNER_TRIPLE_MM, RADIUS_OUTER_TRIPLE_MM, angle,
                                  sector_angle)
            outer_single_bed = QPainterPath()
            make_partial_pie_part(outer_single_bed, cx, cy, RADIUS_OUTER_TRIPLE_MM, RADIUS_INNER_DOUBLE_MM, angle,
                                  sector_angle)
            double_bed = QPainterPath()
            make_partial_pie_part(double_bed, cx, cy, RADIUS_INNER_DOUBLE_MM, RADIUS_OUTER_DOUBLE_MM, angle,
                                  sector_angle)

            self.segment_areas[Segment(SECTOR_ORDER[i], Bed.INNER_SINGLE)] = inner_single_bed
            self.segment_areas[Segment(SECTOR_ORDER[i], Bed.TRIPLE)] = triple_bed
            self.segment_areas[Segment(SECTOR_ORDER[i], Bed.OUTER_SINGLE)] = outer_single_bed
            self.segment_areas[Segment(SECTOR_ORDER[i], Bed.DOUBLE)] = double_bed

            self.available_segments_for_score[SECTOR_ORDER[i]].append(Segment(SECTOR_ORDER[i], Bed.OUTER_SINGLE))
            self.available_segments_for_score[SECTOR_ORDER[i] * 2].append(Segment(SECTOR_ORDER[i], Bed.DOUBLE))
            self.available_segments_for_score[SECTOR_ORDER[i] * 3].append(Segment(SECTOR_ORDER[i], Bed.TRIPLE))

            angle += sector_angle

    @staticmethod
    def get_throw_result(location: QPointF) -> Segment:
        for segment, path in DartBoard._get_instance().segment_areas.items():
            if path.contains(location):
                return segment
        return Segment(0, Bed.NONE)

    @staticmethod
    def get_center_estimate(segment: Segment) -> QPointF:
        sector = segment.sector
        bed = segment.bed
        try:
            area = DartBoard._get_instance().segment_areas[segment]
        except KeyError:
            print(segment, 'not in', DartBoard._get_instance().segment_areas.keys())
            return QPointF(0, 0)
        if sector == 25 and bed in [Bed.SINGLE, Bed.INNER_SINGLE, Bed.OUTER_SINGLE]:
            half_ring = ((RADIUS_OUTER_BULL_MM - RADIUS_INNER_BULL_MM) / 2)+RADIUS_INNER_BULL_MM
            return area.toFillPolygon().boundingRect().center().toPoint() + QPointF(0, - half_ring)
        return area.toFillPolygon().boundingRect().center().toPoint()

    @staticmethod
    def aim_dart_at(intended_loc: Union[QPointF, Segment, int], h_dev_mm: float, v_dev_mm: float) -> QPointF:
        if isinstance(intended_loc, int):
            intended_loc = DartBoard.easiest_segment_for_score(intended_loc)
        if isinstance(intended_loc, Segment):
            intended_loc = DartBoard.get_center_estimate(intended_loc)
        return intended_loc + QPointF(*np.random.normal(scale=(h_dev_mm, v_dev_mm)))

    @staticmethod
    def get_segments_for_score(score: int) -> List[Segment]:
        return DartBoard._get_instance().available_segments_for_score[score]

    @staticmethod
    def easiest_segment_for_score(score: int) -> Segment:
        try:
            scores = {segment.bed: segment for segment in DartBoard._get_instance().available_segments_for_score[score]}
            for bed in [Bed.OUTER_SINGLE, Bed.SINGLE, Bed.INNER_SINGLE, Bed.DOUBLE, Bed.TRIPLE]:
                try:
                    return scores[bed]
                except KeyError:
                    pass
            return list(scores.values())[0]
        except IndexError:
            return Segment(0, Bed.NONE)

    @staticmethod
    def get_segment_areas() -> Dict[Segment, QPainterPath]:
        return DartBoard._get_instance().segment_areas

    @staticmethod
    def get_available_scores() -> Dict[int, List[Segment]]:
        return DartBoard._get_instance().available_segments_for_score

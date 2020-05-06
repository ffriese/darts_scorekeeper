import datetime
from collections import defaultdict

from sqlalchemy import Column, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from database import BaseObject
from database.types import SQLPointF, DartIntent
from models.dartboard import Segment, DartBoard, Bed
from models.helper import create_id_column


class Dart(BaseObject.Base):
    __tablename__ = 'darts'
    id = create_id_column('dart')
    time_stamp = Column(DateTime)
    take_id = Column(Integer, ForeignKey('takes.id', ondelete='CASCADE'), nullable=False)
    hit_location = Column(SQLPointF)
    target_location = Column(SQLPointF)
    intent = Column(Enum(DartIntent))
    take = relationship('Take', back_populates='darts',
                        single_parent=True, lazy='joined')  # IF PROBLEMS ARISE RE-ADD passive_deletes='all' !!

    def __init__(self, take: "Take", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.take = take
        self.time_stamp = datetime.datetime.now()
        print('NEW DART IN ', self.take)

    def get_segment(self) -> Segment:
        return DartBoard.get_throw_result(self.hit_location)

    def get_field_string(self) -> str:
        segment = self.get_segment()
        return '%s%s' % (defaultdict(str, {
            Bed.TRIPLE: 'T',
            Bed.DOUBLE: 'D'
        })[segment.bed], segment.sector)

    def get_score(self) -> int:
        return self.get_segment().score()

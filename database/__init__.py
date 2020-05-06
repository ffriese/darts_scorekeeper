from sqlalchemy.ext.declarative import declarative_base


class BaseObject:
    Base = declarative_base()
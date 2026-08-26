from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class LocalBase(DeclarativeBase):
    metadata = MetaData()

class RemoteBase(DeclarativeBase):
    metadata = MetaData()

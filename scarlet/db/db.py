from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from pydantic import BaseModel
import datetime as dt

import scarlet.db.models as models


class Database:

    def __init__(self):
        self.engine = create_engine('sqlite:///mydb.db', echo=True)
        models.Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add(self, item: BaseModel, model: models.Base):
        model_items = item.dict()
        model_items.update({'timestamp': dt.datetime.now()})
        self.session.add(model(**model_items))
        self.session.commit()

    def get_last(self, model: models.Base):
        return self.session.query(model).order_by(model.timestamp).first()


service = Database()

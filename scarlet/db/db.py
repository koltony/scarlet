from sqlmodel import Session, SQLModel, create_engine, select
from typing import Optional
import datetime as dt

import core.log as log_
import core.config as config

log = log_.service.logger("db")


class Database(config.Component):
    def __init__(self, name):
        super().__init__(name=name)
        self.database = config.ConfigOption(required=True).string  # type: str
        self.engine = None
        self.session = None  # type: Optional[Session]

    def initialize(self):
        self.engine = create_engine(f'sqlite:///{self.database}', echo=False)
        log_.service.change_logger('sqlalchemy.engine.Engine', log_.LogLevels.info)
        log_.service.change_logger('sqlalchemy.orm.mapper.Mapper', log_.LogLevels.info)
        SQLModel.metadata.create_all(bind=self.engine)
        self.session = Session(self.engine)

    def clear_old_data(self, model, time: dt.datetime):
        data = self.session.exec(select(model).where(model.timestamp < time)).all()
        log.info(f"deleting {len(data)} items")
        self.session.delete(data)

    def add(self, item: SQLModel):
        self.session.add(item)
        self.session.commit()

    def get_last(self, model):
        last = self.session.exec(select(model).order_by(model.timestamp)).first()
        if not last:
            log.warning("No data available, cannot get last")
        return last


service = Database('Database')

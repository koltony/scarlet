from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy import Engine
import datetime as dt

import scarlet.core.log as log_
import scarlet.core.config as config

log = log_.service.logger("db")


class Database(config.Service):
    class Config(config.Service.Config):
        database: str

    engine: Engine | None = None
    session: Session | None = None

    def initialize(self):
        self.engine = create_engine(f'sqlite:///{self.config.database}', echo=False)
        log_.service.change_logger('sqlalchemy.engine.Engine', log_.LogLevels.info)
        log_.service.change_logger('sqlalchemy.orm.mapper.Mapper', log_.LogLevels.info)
        SQLModel.metadata.create_all(bind=self.engine)
        self.session = Session(self.engine)
        log.debug(f"database initialized")

    def clear_old_data(self, model, time: dt.datetime):
        data = self.session.exec(select(model).where(model.timestamp < time)).all()
        log.info(f"deleting {len(data)} items")
        if data:
            [self.session.delete(d) for d in data]
            self.session.commit()

    def clear_data_after(self, model, time: dt.datetime):
        data = self.session.exec(select(model).where(model.timestamp > time)).all()
        log.info(f"deleting {len(data)} items")
        if data:
            [self.session.delete(d) for d in data]
            self.session.commit()

    def add(self, item: SQLModel):
        self.session.add(item)
        self.session.commit()

    def add_all(self, items: list[SQLModel]):
        self.session.add_all(items)
        self.session.commit()

    def get_last(self, model):
        last = self.session.exec(select(model).order_by(model.timestamp.desc())).first()
        if not last:
            log.warning("No data available, cannot get last")
        return last


service = Database('Database')

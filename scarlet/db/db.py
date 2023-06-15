from sqlmodel import Session, SQLModel, create_engine, select
import logging
import scarlet.db.models
import scarlet.core.log as log_

log = log_.service.logger("db")


class Database:

    def __init__(self):
        self.engine = create_engine('sqlite:///mydb.db', echo=False)
        log_.service.change_logger('sqlalchemy.engine.Engine', log_.LogLevels.info)
        log_.service.change_logger('sqlalchemy.orm.mapper.Mapper', log_.LogLevels.info)
        SQLModel.metadata.create_all(bind=self.engine)
        self.session = Session(self.engine)

    def add(self, item: SQLModel):
        self.session.add(item)

    def get_last(self, model):
        last = self.session.exec(select(model).order_by(model.timestamp)).first()
        if not last:
            log.warning(f"No data available, cannot get last")
        return last


service = Database()

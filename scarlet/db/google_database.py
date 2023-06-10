import firebase_admin
from firebase_admin import credentials, db, App
from typing import Optional, Dict
import traceback
from scarlet.core import log as log_, config

log = log_.service.logger('google_database')


class FirebaseRealtimeDatabase(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.app_name = config.ConfigOption(required=True).string  # type: str
        self.credentials = config.ConfigOption(required=True).secret  # type: str
        self.database_url = config.ConfigOption(required=True).string  # type: str
        self.app = None  # type: Optional[App]
        self.listened_data = dict()  # type: Dict[str, Optional[db.Event]]

    def initialize(self):
        self.app = firebase_admin.initialize_app(credentials.Certificate(self.credentials), {'databaseURL': self.database_url}, name=self.app_name)

    def close_connection(self):
        try:
            firebase_admin.delete_app(self.app)
            log.info(f"Closing google database: {self.app_name} was successful")
        except Exception as e:
            log.error(f"Could not close google database: {traceback.format_exc()}")

    def _on_message(self, obj: db.Event):
        log.debug(f'message from realtime database from: {obj.path}')
        self.listened_data[obj.path] = obj

    def listen_to(self, reference: str = '/'):
        try:
            db.reference(path=reference, app=self.app).listen(self._on_message)
        except Exception as e:
            log.error(f" Listening to '{reference}' {traceback.format_exc()}")

    def get_update(self, reference='/') -> Optional[dict]:
        data = self.listened_data.get(reference)
        if data:
            self.listened_data[reference] = None
            if data.data:
                log.info(f'Got data for: {reference} ')
                return data.data
        return None

    def set_data(self, data: dict, reference: str = '/'):
        log.debug(f"Set data for: {reference}")
        try:
            db.reference(path=reference, app=self.app).set(data)
        except Exception as e:
            log.error(e)

    def get_data(self, reference: str = '/', etag: bool = False):
        try:
            return db.reference(path=reference, app=self.app).get(etag=etag)
        except Exception as e:
            log.error(e)
            return None


service = FirebaseRealtimeDatabase('FirebaseRealtimeDatabase')

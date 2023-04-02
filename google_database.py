import firebase_admin
from firebase_admin import credentials, db, App
from typing import Optional, Dict
import config
import log as log_

log = log_.service.logger('google_database')


class FirebaseRealtimeDatabase(config.Component):
    def __init__(self, name):
        super().__init__(name)
        self.credentials = config.ConfigOption(required=True).secret
        self.database_url = config.ConfigOption(required=True).string  # type: str
        self.app = None  # type: Optional[App]
        self.listened_data = dict()  # type: Dict[str, firebase_admin.db.Event]

    def initialize(self):
        self.app = firebase_admin.initialize_app(credentials.Certificate(self.credentials), {'databaseURL': self.database_url})

    def _on_message(self, obj: firebase_admin.db.Event):
        log.debug(f'message from realtime database from: {obj.path}')
        self.listened_data[obj.path] = obj

    def listen_to(self, reference: str = '/'):
        db.reference(reference).listen(self._on_message)

    @staticmethod
    def set_data(data: dict, reference: str = '/'):
        log.debug(f"Set data for: {reference}")
        db.reference(reference).set(data)

    @staticmethod
    def get_data(reference: str = '/', etag: bool = False):
        return db.reference(reference).get(etag=etag)


service = FirebaseRealtimeDatabase('FirebaseRealtimeDatabase')

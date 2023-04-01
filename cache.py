import diskcache
import time
from collections import defaultdict
from dataclasses import dataclass
import datetime as dt
import diskcache
from typing import Optional, Dict, List


import config
import log as log_

log = log_.service.logger('cache')


@dataclass
class CachedObject:
    timestamp = dt.datetime.now()

    def __post_init__(self):
        self.name = self.__class__.__name__


class Cache(config.Component):

    def __init__(self, name):
        super().__init__(name)
        self.cache_directory = config.ConfigOption(required=True).string  # type: str
        self.cache_max_age = config.ConfigOption(required=True).integer  # type: int
        self.cache = None  # type: Optional[diskcache.Cache]

    def __len__(self):
        return len(self.cache)

    def initialize(self):
        with diskcache.Cache(directory=self.cache_directory) as cache:
            self.cache = cache

    def clear_cache(self):
        self.cache.clear()
        log.debug(f'{self.name} cache cleared')

    def cache_data(self, data: CachedObject):
        self.clear_old_cache_data()
        self.cache[f'{data.timestamp}_{self.name}'] = data
        log.debug(f'{self.name} data cached: {data}')

    def clear_old_cache_data(self):
        limit = dt.datetime.now() - dt.timedelta(days=self.cache_max_age)
        log.debug(f'removing weather data before {limit}')
        keys_for_removal = list()
        for name in self.cache.iterkeys():
            weather = self.cache[name]
            if limit > weather.timestamp:
                keys_for_removal.append(name)
        log.debug(f'removed {len(keys_for_removal)} weather data points from {self.name}')
        for x in keys_for_removal:
            del self.cache[x]

    def retrieve_data_for_period(self, start: dt.datetime = None, stop: dt.datetime = None) -> Optional[List[CachedObject]]:
        retrieved_data = list()

        if start is None:
            start = dt.datetime.now() - dt.timedelta(days=self.cache_max_age)

        if stop is None:
            stop = dt.datetime.now()

        if len(self.cache) > 0:
            for name in self.cache.iterkeys():
                data = self.cache[name]
                if stop > data.timestamp > start:
                    retrieved_data.append(data)
            log.debug(f"retrieved {len(retrieved_data)} datapoints from {self.name} for {start}:{stop}")
            return retrieved_data
        log.warning(f"No available datapoints from {self.name} for {start}:{stop}")
        return None

    def retrieve_hourly_data_for_day(self) -> Optional[Dict[int, List[CachedObject]]]:
        now = dt.datetime.now()
        retrieved_data = {x+1: (now - dt.timedelta(hours=x), now - dt.timedelta(hours=x+1)) for x in range(0, 25)}
        data = defaultdict(list)
        for name, times in retrieved_data.items():
            period = self.retrieve_data_for_period(times[0], times[1])
            if period:
                data[name] = period
        if data:
            return data
        else:
            log.warning(f"No available datapoints from the last 24 hours")
            return None

    def retrieve_last_from_cache(self) -> Optional[CachedObject]:
        if len(self.cache) >= 1:
            data = self.cache[self.cache.peekitem(last=True)[0]]
            log.debug(f'From {self.name} retrieved last datapoint from cache: {data}')
            return data
        else:
            log.warning(f'No data found in {self.name}')
            return None


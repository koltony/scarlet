import weather

weather.service.refresh_data()
print(weather.service.clouds)
print(weather.service.retrieve_from_cache())


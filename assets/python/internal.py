import json

from motor.motor_asyncio import AsyncIOMotorClient

from typing import Any

class Internal:
	def __init__(self):
		class Constants:
			def __init__(self, constants_file: str):
				self.constants_file = constants_file
				self.cache = {}

			def fetch(self, key: str) -> Any:
				with open(self.constants_file, "r") as file:
					constants = json.load(file)
					
				self.cache.update(
					{
						key: constants[key]
					}
				)
				return self.constants.get(key)

			def get(self, key: str) -> Any:
				return self.cache.get(key)

		self.Constants = Constants

		class Client:
			def __init__(self):
				constants = self.Constants("constants.json")
				self.id = constants.fetch("CLIENT_ID")
				self.core_guild_id = constants.fetch("CORE_GUILD_ID")
				self.token = constants.fetch("CLIENT_TOKEN")

		self.Client = Client

		class Dynamic:
			def __init__(self):
				constants = self.Constants("constants.json")
				mongo = constants.fetch("MONGO")
				client = AsyncIOMotorClient(mongo)
				self.collection = client["core"]["dynamic"]

			async def fetch(self, key: str) -> Any:
				value = await self.collection.find_one({"_id": "constants"}).get(key)
				self.cache.update(
					{
						key: value
					}
				)
				return value

			async def get(self, key: str) -> Any:
				return self.cache.get(key)

		self.Dynamic = Dynamic
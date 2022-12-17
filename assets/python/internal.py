import json
import fastapi
import asyncio
import datetime

from types import coroutine

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
				return constants.get(key)

			def get(self, key: str) -> Any:
				return self.cache.get(key)

		setattr(self, "Constants", Constants)

		class Client:
			def __init__(self, constants: Constants):
				self.id = constants.fetch("CLIENT_ID")
				self.core_guild_id = constants.fetch("CORE_GUILD_ID")
				self.token = constants.fetch("CLIENT_TOKEN")

		setattr(self, "Client", Client)

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

		setattr(self, "Dynamic", Dynamic)

class ApplicationSyncManager:
	def __init__(self):
		internal = Internal()
		constants = internal.Constants("./assets/json/constants.json")
		constants.fetch("MONGO")
		self.constants = constants

	async def send_action_packet(self, packet: dict):
		"""
		Schema:
		{
			"action": 101,
			"data": {
				"member_id": SNOWFLAKE_ID,
				"channel_id": SNOWFLAKE_ID
			}
		}
		"""
		if packet.get("data") is not None:
			task_id = f"{int(datetime.datetime.utcnow().timestamp())}"
			packet.update(
				{
					"task_id": task_id,
					"status": "pending"
				}
			)
			mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
			collection = mongo["core"]["tasks"]
			await collection.insert_one(packet)
			while True:
				document = await collection.find_one(
					{
						"task_id": packet["task_id"]
					}
				)
				if document is not None and document.get("status") != "pending":
					await collection.delete_one(document)
					return document

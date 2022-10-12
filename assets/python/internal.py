import asyncio

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
		self._send_queue = []

	def start(self):
		asyncio.create_task(self._dispatch_sync_loop())

	async def _dispatch_sync_loop(self):
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["senarc-core"]["tasks"]
		while True:
			for payload in await collection.find(
				{
					"status": "completed"
				}
			):
				await collection.delete_one(payload)

			for payload in self._send_queue:
				await collection.insert_one(payload)

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
		if (
			str(packet.get("action")).startswith("1") and len(str(packet.get("action"))) >= 3
		) and (
			packet.get("data") is not None
		):
			return self._send_queue.append(packet)
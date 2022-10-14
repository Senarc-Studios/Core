import json
import asyncio
import datetime
import threading

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
		self._completed_task_queue = []
		self.is_running = False

	def start(self):
		if not self.is_running:
			self.is_running = True
			_fetch_loop = asyncio.get_event_loop()
			_fetch_loop.run_until_complete(self._dispatch_fetch_loop())
			_send_loop = asyncio.get_event_loop()
			_send_loop.run_until_complete(self._dispatch_send_loop())

			_fetch_loop.close()
			_send_loop.close()

		else:
			raise RuntimeError("ASM is already running.")

	async def _dispatch_fetch_loop(self):
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["senarc-core"]["tasks"]
		while True:
			if await collection.count_documents(
				{
					"status": "pending"
				}
			) == 0:
				continue

			documents = collection.find(
				{
					"status": "completed"
				}
			)
			for payload in documents:
				self._completed_task_queue.append(payload)
				await collection.delete_one(payload)

	async def _dispatch_send_loop(self):
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["senarc-core"]["tasks"]
		while True:
			for payload in self._send_queue:
				await collection.insert_one(payload)
				self._send_queue.remove(payload)
			continue

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
			task_id = f"{int(datetime.datetime.now().timestamp())}"
			packet.update(
				{
					"task_id": task_id,
					"status": "pending"
				}
			)
			self._send_queue.append(packet)
			while True:
				for payload in self._completed_task_queue:
					if payload.get("task_id") == task_id:
						return payload.get("data")

					else:
						continue

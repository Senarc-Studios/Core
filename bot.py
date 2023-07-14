import os

from assets.python.internal import Internal

from discord import Intents
from discord.ext.commands import Bot

from typing import Coroutine, Any

class Senarc(Bot):
	def __init__(self, guild_id, *args, **kwargs):
		self.guild_id = guild_id
		super().__init__(*args, **kwargs)

	async def start(self, *args, **kwargs):
		await super().start(*args, **kwargs)

	async def sync_application(self):
		await self.tree.sync(guild = self.guild_id)
		await self.tree.sync()
		print("Application synced successfully.")

	async def setup_hook(self) -> Coroutine[Any, Any, None]:
		for file in os.listdir("./cogs"):
			if file.endswith(".py"):
				await self.load_extension(f"cogs.{file[:-3]}")

		self.loop.create_task(self.sync_application())

fetch_list = (
	"CLIENT_TOKEN",
	"CORE_GUILD_ID"
)
internal = Internal()
Constants = internal.Constants("./assets/json/constants.json")
for constant in fetch_list:
	Constants.fetch(constant)

intents = Intents.all()
bot = Senarc(
	guild_id = int(Constants.get("CORE_GUILD_ID")),
	command_prefix = "sca!",
	intents = intents
)

if __name__ == "__main__":
	bot.Constants = Constants
	bot.run(Constants.get("CLIENT_TOKEN"))
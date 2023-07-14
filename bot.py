import os

from assets.python.internal import Internal

from discord import Intents
from discord.ext.commands import Bot

from typing import Coroutine, Any

class Senarc(Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	async def start(self, *args, **kwargs):
		super().start(*args, **kwargs)

	async def sync_application(self):
		await self.tree.sync(guild = Internal.core_guild)
		print("Application synced successfully.")

	async def setup_hook(self) -> Coroutine[Any, Any, None]:
		for file in os.listdir("./cogs"):
			if file.endswith(".py"):
				self.load_extension(f"cogs.{file[:-3]}")

		self.loop.create_task(self.sync_application())

intents = Intents.all()
bot = Bot(
	command_prefix = "sca!",
	intents = intents
)

fetch_list = (
	"TOKEN"
)
internal = Internal()
Constants = internal.Constants
for constant in fetch_list:
	Constants.fetch(constant)

if __name__ == "__main__":
	bot.Constants = Constants
	bot.run(Constants.TOKEN)
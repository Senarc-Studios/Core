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

	# async def setup_hook(self) -> Coroutine[Any, Any, None]:
	# 	for file in os.listdir("./assets/python/bot"):
	# 		if file.endswith(".py"):
	# 			self.load_extension(f"assets.python.bot.{file[:-3]}")

bot = Bot(
	command_prefix = "sca!",
	intents = intents
)

fetch_list = (
	"TOKEN"
)
internal = Internal(bot)
Constants = internal.Constants
for constant in fetch_list:
	Constants.fetch(constant)

if __name__ == "__main__":
	bot.Constants = Constants
	bot.run(Constants.TOKEN)
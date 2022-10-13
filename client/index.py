import asyncio

from assets.python.internal import Internal

from cool_utils import Terminal
from motor.motor_asyncio import AsyncIOMotorClient

from discord import Embed, Intents
from discord.ext.commands import Bot

Internal = Internal()
Constants = Internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CLIENT_TOKEN",
	"CHANNELS",
	"MONGO",
	"ROLES",
	"ENVIRONMENT"
)
intents = Intents.all()
bot = Bot(
	command_prefix = "sca!",
	intents = intents
)

for constant in fetch_list:
	Constants.fetch(constant)

class ApplicationManagementUnit:
	def __init__(self):
		self.bot = bot
		self.constants = Constants

	async def start(self):
		try:
			self.bot.run(Constants.get("CLIENT_TOKEN"))
		except Exception as error:
			print(error)
		asyncio.create_task(self._loop_task_fetch())

	async def _loop_task_fetch(self):
		await asyncio.sleep(0.01)
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["senarc-core"]["tasks"]
		while True:
			payload = await collection.find_one(
				{
					"status": "pending"
				}
			)
			if payload is not None:
				action_type = payload["action"]
				if action_type == 101:
					data = payload["data"]
					core_guild = await self.bot.fetch_guild(self.constants.get("CORE_GUILD"))
					member = await core_guild.fetch_member(data["member_id"])
					channel = await self.bot.fetch_channel(data["channel_id"])
					try:
						await member.move_to(channel)
						await collection.update_one(
							{
								"task_id": payload["task_id"]
							},
							{
								"$set": {
									"status": "completed"
								}
							}
						)
					except:
						await collection.update_one(
							{
								"task_id": payload["task_id"]
							},
							{
								"$set": {
									"status": "failed",
									"result": {
										"reason": "User not in voice channel."
									}
								}
							}
						)
					continue

@bot.listen("on_ready")
async def startup():
	Terminal.display("Bot is ready.")

@bot.listen("on_member_join")
async def greet_new_members(member):
	Terminal.display(f"{member.name} has joined the guild.")
	embed = Embed(
		timestamp = member.joined_at,
		description = f"Welcome to **Senarc**'s Core Guild, we hope you have a nice stay!",
		colour = 0x35393f
	)
	embed.set_author(
		name = f"{member.name} Joined!",
		icon_url = member.avatar_url
	)
	embed.set_footer(
		text = f"Senarc Core",
		icon_url = bot.user.avatar_url
	)
	role = await member.guild.fetch_role(Constants.get("ROLES").get("MEMBER"))
	await member.add_roles(role)
	await member.guild.system_channel.send(embed = embed)
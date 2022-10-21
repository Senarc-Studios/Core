import sys
import asyncio
import traceback

from assets.python.internal import Internal

from cool_utils import Terminal
from motor.motor_asyncio import AsyncIOMotorClient

from discord import utils, Embed, Intents, AuditLogAction, HTTPException
from discord.ext.commands import Bot, NoPrivateMessage, CommandNotFound

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
			await self.bot.start(Constants.get("CLIENT_TOKEN"))
		except Exception as error:
			print(error)
		await asyncio.create_task(self._loop_task_fetch())

	async def _loop_task_fetch(self):
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["senarc-core"]["tasks"]
		while True:
			if await collection.count_documents(
				{
					"status": "pending"
				}
			) > 0:
				continue
			payload = await collection.find_one(
				{
					"status": "pending"
				}
			)
			if payload is not None:
				print(payload)
				action_type = payload["action"]
				if action_type == 101:
					data = payload["data"]
					core_guild = await self.bot.fetch_guild(self.constants.get("CORE_GUILD"))
					member = await core_guild.fetch_member(data["member_id"])
					channel = await self.bot.fetch_channel(data["channel_id"])
					if channel is None:
						await collection.update_one(
							{
								"_id": payload["_id"]
							},
							{
								"$set": {
									"status": "failed",
									"result": {
										"reason": "Channel not found."
									}
								}
							}
						)
						continue
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

				elif action_type == 102:
					data = payload["data"]
					core_guild = await self.bot.fetch_guild(self.constants.get("CORE_GUILD"))
					member = await core_guild.fetch_member(data["member_id"])
					channel = await self.bot.fetch_channel(data["channel_id"])
					if channel is None:
						await collection.update_one(
							{
								"task_id": payload["task_id"]
							},
							{
								"$set": {
									"status": "failed",
									"result": {
										"reason": "Channel not found."
									}
								}
							}
						)
						continue
					if member in channel.members:
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
					else:
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
	Terminal.display(f"{member.name} has joined the guild.") if not bot else Terminal.display(f"{member.name} Bot has joined the guild.")

	while member.pending:
		await asyncio.sleep(1)
		continue

	if member.bot:
		log_channel = utils.get(
			member.guild.channels,
			id = int(Constants.get("CHANNELS").get("LOGS"))
		)
		async for entry in member.guild.audit_logs(
			action = AuditLogAction.bot_add
		):
			log_entry = entry if entry.target == member and entry.target.joined_at == member.joined_at else log_entry

		author = log_entry.user
		added_bot = log_entry.target

		embed = Embed(
			timestamp = added_bot.joined_at,
			description = f"<@!{added_bot.id}> Bot has been added to the guild by <@!{author.id}>.",
			colour = 0x2f3136
		)
		embed.set_author(
			name = f"{added_bot.name} Bot Added!",
			icon_url = added_bot.display_avatar.url
		)
		embed.set_footer(
			text = f"Senarc Core",
			icon_url = bot.user.display_avatar.url
		)
		role = utils.get(
			added_bot.guild.roles,
			id = int(Constants.get("ROLES").get("BOT"))
		)
		await added_bot.add_roles(role)
		await log_channel.send(
			embed = embed
		)

	else:
		embed = Embed(
			timestamp = member.joined_at,
			description = f"Welcome to **Senarc**'s Core Guild, we hope you have a nice stay!",
			colour = 0x2f3136
		)
		embed.set_author(
			name = f"{member.name} Joined!",
			icon_url = member.display_avatar.url
		)
		embed.set_footer(
			text = f"Senarc Core",
			icon_url = bot.user.display_avatar.url
		)
		role = utils.get(
			member.guild.roles,
			id = int(Constants.get("ROLES").get("MEMBER"))
		)
		await member.add_roles(role)
		await member.guild.system_channel.send(
			content = f"<@!{member.id}>",
			embed = embed
		)

# Source: https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
@bot.listen("on_command_error")
async def error_handler(ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (CommandNotFound)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, NoPrivateMessage):
            try:
                await ctx.author.send(f'`{ctx.command}` can not be used in Private Messages.')
            except HTTPException:
                pass

        else:
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

if __name__ == "__main__":
	ApplicationManagementUnit = ApplicationManagementUnit()
	asyncio.run(ApplicationManagementUnit.start())
import sys
import aiohttp
import asyncio
import datetime
import traceback

from cool_utils import Terminal
from motor.motor_asyncio import AsyncIOMotorClient

from discord import utils, Thread, Embed, Intents, AuditLogAction, HTTPException
from discord.ext.commands import Bot, NoPrivateMessage, CommandNotFound

from assets.python.internal import Internal
from assets.python.type import ActionPacket, Modmail, CreateVoice

Internal = Internal()
Constants = Internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CLIENT_TOKEN",
	"CORE_GUILD_ID",
	"CHANNELS",
	"MONGO",
	"ROLES",
	"ENVIRONMENT"
)
intents = Intents.all()
ENDPOINT_URL = "https://discord.com/api/v10"

class Senarc(Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	async def start(self, *args, **kwargs):
		super().start(*args, **kwargs)

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

	async def _loop_task_fetch(self):
		mongo = AsyncIOMotorClient(self.constants.get("MONGO"))
		collection = mongo["core"]["tasks"]
		while True:
			if await collection.count_documents(
				{
					"status": "pending"
				}
			) == 0:
				continue
			payload = await collection.find_one(
				{
					"status": "pending"
				}
			)
			if payload is not None:
				print(payload)
				interaction_type = payload["interaction"]
				action_type = payload["action"]
				if interaction_type is ActionPacket.CALLBACK:
					if action_type == Modmail.Action.CHECK_THREAD_EXISTANCE:
						try:
							member_id = payload["data"]["member_id"]
							forum_channel = bot.get_channel(int(Constants.get("CHANNELS").get("MODMAIL_FORUM")))

							thread_exists = False
							for thread in forum_channel.threads:
								starter_message = await thread.fetch_message(thread.id)
								if (str(member_id) == starter_message.content) and (not thread.locked and not thread.archived):
									thread_exists = True
									break

							if thread_exists:
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
								continue

							else:
								await collection.update_one(
									{
										"task_id": payload["task_id"]
									},
									{
										"$set": {
											"status": "failed",
											"result": {
												"reason": "Thread already exists."
											}
										}
									}
								)
								continue
						except Exception as e:
							print(e)

					elif action_type == Modmail.Action.THREAD_DELETE:
						try:
							member_id = payload["data"]["id"]
							payload_type = payload["data"]["type"]
							forum_channel = bot.get_channel(int(Constants.get("CHANNELS").get("MODMAIL_FORUM")))

							if payload_type == Modmail.InteractionType.DM:
								for thread in forum_channel.threads:
									starter_message = await thread.fetch_message(thread.id)
									if (str(member_id) == starter_message.content) and (not thread.locked and not thread.archived):
										await thread.edit(archived = True)
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
										continue

							elif payload_type == Modmail.InteractionType.THREAD:
								thread = await forum_channel.fetch_thread(payload["data"]["id"])
								await thread.edit(archived = True)
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
								continue

							await collection.update_one(
								{
									"task_id": payload["task_id"]
								},
								{
									"$set": {
										"status": "failed",
										"result": {
											"reason": "Thread not found."
										}
									}
								}
							)
							continue
						except Exception as e:
							print(e)
							await collection.update_one(
								{
									"task_id": payload["task_id"]
								},
								{
									"$set": {
										"status": "failed",
										"result": {
											"reason": "Thread not found."
										}
									}
								}
							)
							continue

					else:
						continue

				elif interaction_type == ActionPacket.HANDOFF:
					action_type = payload["action"]
					if action_type == CreateVoice.CREATE_CHANNEL:
						try:
							member_id = payload["data"].get("member_id")
							interaction = payload["data"].get("interaction")
							guild = bot.get_guild(int(Constants.get("CORE_GUILD_ID")))
							member = await guild.fetch_member(member_id)
							channel = await guild.fetch_channel(interaction["channel_id"])
							await collection.update_one(
								{
									"task_id": payload["task_id"]
								},
								{
									"$set": {
										"status": "completed"
									}
								}
							) if member is not None and channel is not None and interaction.get("token") else await collection.update_one(
								{
									"task_id": payload["task_id"]
								},
								{
									"$set": {
										"status": "failed"
									}
								}
							)
							if member in channel.members:
								async with aiohttp.ClientSession() as session:
									async with session.post(
										f"{ENDPOINT_URL}/guilds/{Constants.get('CORE_GUILD_ID')}/channels",
										headers={
											"Authorization": f"BOT {Constants.get('CLIENT_TOKEN')}"
										},
										json={
											"name": f"{interaction['member']['user']['username']}'s VC",
											"type": 2,
											"parent_id": Constants.get("CHANNELS")['VOICE_CATEGORY'],
											"permission_overwrites": [
												{
													"id": interaction["member"]["user"]["id"],
													"type": 1,
													"allow": 554385280784
												},
												{
													"id": Constants.get('CORE_GUILD_ID'),
													"type": 0,
													"deny": 1024
												}
											]
										}
									) as resp:
										await session.post(
											f"{ENDPOINT_URL}/interactions/{interaction['id']}/{interaction['token']}/callback",
											headers={
												"Authorization": f"BOT {Constants.get('CLIENT_TOKEN')}"
											},
											json = {
												"type": 4,
												"data": {
													"content": f"{Constants.get('EMOJIS')['SUCCESS']} Your Voice Channel has been created! <#{await resp.json()['id']}>"
												}
											}
										)
										channel = await bot.fetch_channel(await resp.json()["id"])
										await member.move_to(channel)
										continue
							else:
								async with aiohttp.ClientSession() as session:
									await session.post(
										f"{ENDPOINT_URL}/interactions/{interaction['id']}/{interaction['token']}/callback",
										headers={
											"Authorization": f"BOT {Constants.get('CLIENT_TOKEN')}"
										},
										json = {
											"type": 4,
											"data": {
												"content": f"{Constants.get('EMOJIS')['FAIL']} You must be in the voice channel to create your voice channel."
											}
										}
									)
									continue
						except Exception as e:
							traceback.print_exc(e)
							await collection.update_one(
								{
									"task_id": payload["task_id"]
								},
								{
									"$set": {
										"status": "failed",
										"result": {
											"reason": "Failed to create voice channel."
										}
									}
								}
							)
							continue

				else:
					continue

@bot.listen("on_ready")
async def startup():
	Terminal.display("Bot is ready.")
	await bot.ApplicationManagementUnit._loop_task_fetch()

@bot.listen("on_member_join")
async def greet_new_members(member):
	Terminal.display(f"{member.name} has joined the guild.") if not member.bot else Terminal.display(f"{member.name} Bot has joined the guild.")

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
		mongo = AsyncIOMotorClient(bot.ApplicationManagementUnit.constants.get("MONGO"))
		collection = mongo["senarc"]["members"]
		member_data = await collection.find_one(
			{
				"member_id": member.id
			}
		)

		if member_data is not None:
			for role in member_data["roles"]:
				role = utils.get(
					member.guild.roles,
					id = int(role)
				)
				await member.add_roles(role)

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

		log_channel = utils.get(
			member.guild.channels,
			id = int(Constants.get("CHANNELS").get("MEMBER_LOGS"))
		)

		embed = Embed(
			timestamp = datetime.datetime.utcnow(),
			description = f"{member.name}#{member.discriminator} (`{member.id}`) has joined the guild.",
			colour = 0x2f3136
		)

		embed.set_author(
			name = f"{member.name} Joined",
			icon_url = member.display_avatar.url
		)

		embed.set_footer(
			text = f"Senarc Core",
			icon_url = bot.user.display_avatar.url
		)

		await log_channel.send(
			embed = embed
		)

@bot.listen("on_member_remove")
async def log_bot_removes(member):
	Terminal.display(f"{member.name} has left the guild.") if not member.bot else Terminal.display(f"{member.name} Bot has been removed from the guild.")

	if member.bot:
		log_channel = utils.get(
			member.guild.channels,
			id = int(Constants.get("CHANNELS").get("LOGS"))
		)
		async for entry in member.guild.audit_logs(
			action = AuditLogAction.kick
		):
			log_entry = entry if entry.target == member and entry.target.joined_at == member.joined_at else log_entry

		author = log_entry.user
		added_bot = log_entry.target

		embed = Embed(
			timestamp = datetime.datetime.utcnow(),
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
		log_channel = utils.get(
			member.guild.channels,
			id = int(Constants.get("CHANNELS").get("MEMBER_LOGS"))
		)

		embed = Embed(
			timestamp = datetime.datetime.utcnow(),
			description = f"{member.name}#{member.discriminator} (`{member.id}`) has left the guild.",
			colour = 0x2f3136
		)

		embed.set_author(
			name = f"{member.name} Left",
			icon_url = member.display_avatar.url
		)

		embed.set_footer(
			text = f"Senarc Core",
			icon_url = bot.user.display_avatar.url
		)

		await log_channel.send(
			embed = embed
		)

@bot.listen("on_message")
async def modmail(message):
	if not message.author.bot and message.guild == None:
		try:
			thread_author_id = str(message.author.id)

			forum_channel = bot.get_channel(int(Constants.get("CHANNELS").get("MODMAIL_FORUM")))

			thread_exists = False
			for thread in forum_channel.threads:
				starter_message = await thread.fetch_message(thread.id)
				if (thread_author_id == starter_message.content) and (not thread.locked and not thread.archived):
					thread_exists = True
					break

			if thread_exists:
				embed = Embed(
					timestamp = datetime.datetime.utcnow(),
					description = message.content,
					colour = 0x303136
				)
				embed.set_author(
					name = f"{message.author.name}#{message.author.discriminator}",
					icon_url = message.author.display_avatar.url
				)
				embed.set_footer(
					text = f"Senarc Core",
					icon_url = bot.user.display_avatar.url
				)
				image_embeds = [embed]
				if message.attachments:
					if not len(message.attachments) > 1:
						embed.add_field(
							name = f"> Attachment",
							value = f"[{message.attachments[0].filename}]({message.attachments[0].url})"
						)
						embed.set_image(
							url = message.attachments[0].url
						)

					else:
						for attachment in message.attachments:
							image_embed = Embed(
								timestamp = datetime.datetime.utcnow(),
								colour = 0x303136
							)
							image_embed.set_author(
								name = f"{attachment.filename}",
								url = attachment.url
							)
							image_embed.set_image(
								url = attachment.url
							)
							image_embeds.append(image_embed)

				if len(image_embeds) > 0:
					await thread.send(
						embeds = image_embeds
					)

				else:
					await thread.send(
						embed = embed
					)
				await message.add_reaction("<:ModMailSent:1040971440515731456>")

			else:
				return

		except Exception as error:
			traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	elif isinstance(message.channel, Thread):
		if message.channel.parent_id == int(Constants.get("CHANNELS").get("MODMAIL_FORUM")) and not message.content.startswith("!"):
			try:
				if not message.author.bot:
					starter_message = message.channel.starter_message
					if not starter_message:
						starter_message = await message.channel.fetch_message(message.channel.id)
					user = await bot.fetch_user(int(starter_message.content))
					embed = Embed(
						timestamp = datetime.datetime.utcnow(),
						description = message.content,
						colour = 0x303136
					)
					embed.set_author(
						name = f"Modmail System",
						icon_url = bot.user.display_avatar.url
					)
					embed.set_footer(
						text = f"Senarc Core",
						icon_url = bot.user.display_avatar.url
					)
					image_embeds = [embed]
					if message.attachments:
						if not len(message.attachments) > 1:
							embed.add_field(
								name = f"> Attachment",
								value = f"[{message.attachments[0].filename}]({message.attachments[0].url})"
							)
							embed.set_image(
								url = message.attachments[0].url
							)

						else:
							for attachment in message.attachments:
								image_embed = Embed(
									timestamp = datetime.datetime.utcnow(),
									colour = 0x303136
								)
								image_embed.set_author(
									name = f"{attachment.filename}",
									url = attachment.url
								)
								image_embed.set_image(
									url = attachment.url
								)
								image_embeds.append(image_embed)

					if len(image_embeds) > 0:
						await user.send(
							embeds = image_embeds
						)

					else:
						await user.send(
							embed = embed
						)
					await message.add_reaction("<:ModMailSent:1040971440515731456>")

			except Exception as error:
				traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	else:
		mongo = AsyncIOMotorClient(bot.ApplicationManagementUnit.constants.get("MONGO"))
		collection = mongo["senarc"]["members"]

		if await collection.count_documents(
			{
				"member_id": message.author.id
			}
		) == 0:
			if len(message.author.roles) <= 1:
				return

			else:
				await collection.insert_one(
					{
						"member_id": message.author.id,
						"roles": [role.id for role in message.author.roles]
					}
				)

		else:
			member_data = await collection.find_one(
				{
					"member_id": message.author.id
				}
			)
			not_in_user = [
				role
				for role in member_data["roles"] if role not in [
					role.id
					for role in message.author.roles
				]
			]
			new_roles = [
				role.id
				for role in message.author.roles if role.id not in member_data["roles"]
			]
			await collection.update_one(
				{
					"member_id": message.author.id
				},
				{
					"$addToSet": {
						"roles": {
							"roles": new_roles
						}
					},
					"$pull": {
						"roles": {
							"roles": not_in_user
						}
					}
				}
			)

# Source: https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
@bot.listen("on_command_error")
async def error_handler(ctx, error):
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
	bot.ApplicationManagementUnit = ApplicationManagementUnit()
	asyncio.run(bot.ApplicationManagementUnit.start())
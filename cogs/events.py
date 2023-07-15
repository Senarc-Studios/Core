import re
import sys
import aiohttp
import asyncio
import traceback

from assets.python.internal import Internal

from discord import AuditLogAction, Embed, Intents, Thread, utils
from discord.ext.commands import Cog

from datetime import datetime
from cool_utils import Terminal # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient

Internal = Internal()
Constants = Internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CLIENT_TOKEN",
	"CORE_GUILD_ID",
	"CHANNELS",
	"MONGO",
	"ROLES",
	"ENVIRONMENT",
    "GITHUB_TOKEN"
)
for constant in fetch_list:
    Constants.fetch(constant)
intents = Intents.all()
ENDPOINT_URL = "https://discord.com/api/v10"
DISCORD_TOKEN_REGEX = re.compile(r"([a-zA-Z0-9-_.]{23,28}\.[a-zA-Z0-9-_.]{6,7}\.[a-zA-Z0-9-_.]{38})")

class Events(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener("on_member_update")
    async def autorole(self, member_before, member_after):
        if member_before.pending and not member_after.pending:
            quarentine_role = utils.get(
                member_after.guild.roles,
                id = int(Constants.get("ROLES").get("QUARENTINE"))
            )
            while quarentine_role in member_after.roles and quarentine_role not in member_before.roles:
                try:
                    member_exists = await member_after.guild.fetch_member(member_after.id)
                    if member_exists:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return
                except:
                    return

            if quarentine_role in member_after.roles and quarentine_role in member_before.roles:
                return

            try:
                await member_after.guild.fetch_member(member_after.id)
            except:
                return

            role = utils.get(
                member_after.guild.roles,
                id = int(Constants.get("ROLES").get("MEMBER"))
            )
            await member_after.add_roles(role)
            Terminal.display(f"{member_after.name} has been given the Member role.")

            embed = Embed(
                timestamp = member_after.joined_at,
                description = f"Welcome to **Senarc**'s Core Guild, we hope you have a nice stay!",
                colour = 0x2B2D31
            )
            embed.set_author(
                name = f"{member_after.name} Joined!",
                icon_url = member_after.display_avatar.url
            )
            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )
            await member_after.guild.system_channel.send(
                content = f"<@!{member_after.id}>",
                embed = embed
            )

            mongo = AsyncIOMotorClient(Constants.get("MONGO"))
            collection = mongo["senarc"]["members"]
            member_data = await collection.find_one(
                {
                    "member_id": member_after.id
                }
            )

            if member_data is not None:
                for role in member_data["roles"]:
                    role = utils.get(
                        member_after.guild.roles,
                        id = int(role)
                    )
                    await member_after.add_roles(role)

    @Cog.listener("on_message_delete")
    async def log_deleted_message(self, message):
        if not message.author.bot:
            log_channel = utils.get(
                message.guild.channels,
                id = int(Constants.get("CHANNELS").get("MESSAGE_LOGS"))
            )
            embed = Embed(
                timestamp = message.created_at,
                description = f"{message.author.mention} (`{message.id}`)```\n{message.content}\n```",
                colour = 0x2B2D31
            )
            embed.set_author(
                name = f"{message.author.name} Deleted a Message",
                icon_url = message.author.display_avatar.url
            )
            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )
            await log_channel.send(embed = embed)

    @Cog.listener("on_message_edit")
    async def log_edited_message(self, before, after):
        if not before.author.bot:
            log_channel = utils.get(
                before.guild.channels,
                id = int(Constants.get("CHANNELS").get("MESSAGE_LOGS"))
            )
            embed = Embed(
                timestamp = before.created_at,
                description = f"{before.author.mention} (`{before.author.id}`)\n\n> **Before:**\n```\n{before.content}\n```\n> **After:**\n```\n{after.content}\n```",
                colour = 0x2B2D31
            )
            embed.set_author(
                name = f"{before.author.name} Edited a Message",
                icon_url = before.author.display_avatar.url
            )
            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )
            await log_channel.send(embed = embed)

    @Cog.listener("on_member_join")
    async def greet_new_members(self, member):
        Terminal.display(f"{member.name} has joined the guild.") if not member.bot else Terminal.display(f"{member.name} Bot has joined the guild.")

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
                colour = 0x2B2D31
            )
            embed.set_author(
                name = f"{added_bot.name} Bot Added!",
                icon_url = added_bot.display_avatar.url
            )
            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
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
                description = f"{member.name}#{member.discriminator} (`{member.id}`) has joined the guild.",
                colour = 0x2B2D31
            )

            embed.set_author(
                name = f"{member.name} Joined",
                icon_url = member.display_avatar.url
            )

            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )

            await log_channel.send(
                embed = embed
            )

    @Cog.listener("on_member_remove")
    async def log_bot_removes(self, member):
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
            removed_bot = log_entry.target

            embed = Embed(
                timestamp = datetime.datetime.utcnow(),
                description = f"<@!{removed_bot.id}> Bot has been removed from the guild by <@!{author.id}>.",
                colour = 0x2B2D31
            )
            embed.set_author(
                name = f"{removed_bot.name} Removed!",
                icon_url = removed_bot.display_avatar.url
            )
            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )

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
                colour = 0x2B2D31
            )

            embed.set_author(
                name = f"{member.name} Left",
                icon_url = member.display_avatar.url
            )

            embed.set_footer(
                text = f"Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )

            await log_channel.send(
                embed = embed
            )

    @Cog.listener("on_message")
    async def deactivate_tokens(self, message):
        match = re.search(DISCORD_TOKEN_REGEX, message.content)
        if match:
            token = match.group(0)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://discord.com/api/v10/users/@me",
                    headers = {
                        "Authorization": "Bot " + token,
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status == 401:
                        return
                    else:
                        message_ = await message.reply(content = f"<:Warning:1042680344278741123> Deactivating leaked discord token...")
                        url = "https://api.github.com/gists/0e8566d842864e77d62939e6a277251e"
                        headers = {
                            "Accept": "application/vnd.github+json",
                            "Authorization": f"token {Constants.get('GITHUB_TOKEN')}"
                        }
                        data = {
                            "description": "This is the last Discord Token that was leaked and deactivated",
                            "public": True,
                            "files": {
                                "last_deactivated_token.txt": {
                                    "content": f"{token}\n\nPlease don't leak your token next time.\nAuto Deactivated by Senarc Core"
                                }
                            }
                        }
                        try:
                            async with session.patch(url, headers = headers, json = data) as response:
                                if response.status == 200:
                                    await message_.edit(content = "<:Success:1035574699566051358> Token has been deactivated.")
                                else:
                                    await message_.edit(content = "<:Warning:1042680344278741123> Token could not be deactivated.")
                        except Exception as e:
                            print(e)
                            await message_.edit(content = f"<:Warning:1042680344278741123> An error occurred while trying to deactivate the token: {e}")

    @Cog.listener("on_message")
    async def modmail(self, message):
        if not message.author.bot and message.guild == None:
            try:
                thread_author_id = str(message.author.id)

                forum_channel = self.bot.get_channel(int(Constants.get("CHANNELS").get("MODMAIL_FORUM")))

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
                        icon_url = self.bot.user.display_avatar.url
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
                        user = await self.bot.fetch_user(int(starter_message.content))
                        embed = Embed(
                            timestamp = datetime.datetime.utcnow(),
                            description = message.content,
                            colour = 0x303136
                        )
                        embed.set_author(
                            name = f"Modmail System",
                            icon_url = self.bot.user.display_avatar.url
                        )
                        embed.set_footer(
                            text = f"Senarc Core",
                            icon_url = self.bot.user.display_avatar.url
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
            mongo = AsyncIOMotorClient(Constants.get("MONGO"))
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
                    role.id
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
                            "roles": new_roles
                        },
                        "$pull": {
                            "roles": not_in_user
                        }
                    }
                )

async def setup(bot):
    await bot.add_cog(Events(bot))
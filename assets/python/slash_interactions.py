import os
import sys
import json
import aiohttp
import datetime

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from motor.motor_asyncio import AsyncIOMotorClient

from fastapi import APIRouter
from fastapi import Request

from assets.python.internal import Internal, ApplicationSyncManager

internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CLIENT_PUBLIC_KEY",
	"API_TOKEN",
	"PING_ROLES",
	"CHANNELS",
	"EMOJIS"
)

for constant in fetch_list:
	constants.fetch(constant)

Client = internal.Client(constants)
ApplicationSyncManager = ApplicationSyncManager()

Router = APIRouter(
	prefix="/discord"
)
ENDPOINT_URL = "https://discord.com/api/v10"
UPLOAD_ENDPOINT = f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands"
DISCORD_HEADERS = {
	"Authorization": f"Bot {Client.token}",
	"Content-Type": "application/json"
}

@Router.post("/interaction")
async def interaction_handler(request: Request):
	PUBLIC_KEY = constants.get("CLIENT_PUBLIC_KEY")
	CHANNELS = constants.get("CHANNELS")
	EMOJIS = constants.get("EMOJIS")
	interaction = await request.json()

	verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

	signature = request.headers.get("X-Signature-Ed25519")
	timestamp = request.headers.get("X-Signature-Timestamp")
	body = (await request.body()).decode("utf-8")

	try:
		verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
	except BadSignatureError:
		return 'invalid request signature', 401

	print(json.dumps(interaction, indent=4))

	if interaction["type"] == 1:
		return {
			"type": 1
		}

	if interaction["type"] == 2:
		data = interaction.get("data")
		if data.get("name") == "voice" and data["options"][0]["name"] == "create":
			if not interaction.get("channel_id") == CHANNELS["CREATE_VOICE"]:
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['FAIL']} You can only create a voice channel in <#{CHANNELS['CREATE_VOICE']}>.",
						"flags": 64
					}
				}

			else:
				async with aiohttp.ClientSession() as session:
					async with session.get(
						f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/channels",
						headers = DISCORD_HEADERS
					) as guild_channels:
						guild_channels = await guild_channels.json()
						for channel in guild_channels:
							if channel.get("parent_id") == CHANNELS["VOICE_CATEGORY"]:
								for permissions in channel.get("permission_overwrites"):
									if permissions["id"] == interaction["member"]["user"]["id"] and permissions["allow"] == "554385280784":
										return {
											"type": 4,
											"data": {
												"content": f"{EMOJIS['FAIL']} You already have a voice channel.",
												"flags": 64
											}
										}

									else:
										continue

							else:
								continue

						if (await ApplicationSyncManager.send_action_packet(
							{
								"action": 102,
								"data": {
									"channel_id": CHANNELS["CREATE_VOICE"],
									"member_id": interaction["member"]["user"]["id"]
								}
							}
						))["status"] == "completed":
							async with session.post(
								f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/channels",
								headers=DISCORD_HEADERS,
								json={
									"name": f"{interaction['member']['user']['username']}'s VC",
									"type": 2,
									"parent_id": CHANNELS['VOICE_CATEGORY'],
									"permission_overwrites": [
										{
											"id": interaction["member"]["user"]["id"],
											"type": 1,
											"allow": 554385280784
										},
										{
											"id": Client.core_guild_id,
											"type": 0,
											"deny": 1024
										}
									]
								}
							) as resp:
								await ApplicationSyncManager.send_action_packet(
									{
										"action": 101,
										"data": {
											"channel_id": (await resp.json())["id"],
											"member_id": interaction["member"]["user"]["id"]
										}
									}
								)
								return {
									"type": 4,
									"data": {
										"content": f"{EMOJIS['SUCCESS']} Created a voice channel: <#{(await resp.json())['id']}>",
										"flags": 64
									}
								}
						else:
							return {
								"type": 4,
								"data": {
									"content": f"{EMOJIS['FAIL']} You need to join the VC to create yours.",
									"flags": 64
								}
							}

		elif data.get("name") == "voice" and data["options"][0]["name"] == "permit":
			sub_action = data["options"][0]["options"][0]
			if sub_action["name"] == "approve":
				async with aiohttp.ClientSession() as session:
					async with session.get(
						f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
						headers = DISCORD_HEADERS
					) as channel:
						channel = await channel.json()
						permission_overwrites = channel["permission_overwrites"]
						permission_overwrites.append(
							{
								"id": sub_action["options"][0]["value"],
								"type": 1,
								"allow": "549792517632"
							}
						)
						async with session.patch(
							f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
							headers = DISCORD_HEADERS,
							json = {
								"permission_overwrites": permission_overwrites
							}
						) as resp:
							return {
								"type": 4,
								"data": {
									"content": f"{EMOJIS['SUCCESS']} Added <@!{sub_action['options'][0]['value']}> to the voice channel.",
									"flags": 64
								}
							}

			elif sub_action["name"] == "deny":
				async with aiohttp.ClientSession() as session:
					async with session.get(
						f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
						headers = DISCORD_HEADERS
					) as channel:
						channel = await channel.json()
						permission_overwrites = channel["permission_overwrites"]
						for overwrites in permission_overwrites:
							if overwrites["id"] == sub_action["options"][0]["value"]:
								permission_overwrites.remove(overwrites)
								break

						async with session.patch(
							f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
							headers = DISCORD_HEADERS,
							json = {
								"permission_overwrites": permission_overwrites
							}
						) as resp:
							return {
								"type": 4,
								"data": {
									"content": f"{EMOJIS['SUCCESS']} Removed <@!{sub_action['options'][0]['value']}> from the voice channel.",
									"flags": 64
								}
							}

		elif data.get("name") == "voice" and data["options"][0]["name"] == "end":
			async with aiohttp.ClientSession() as session:
				async with session.get(
					f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
					headers = DISCORD_HEADERS
				) as channel:
					channel = await channel.json()
					print(json.dumps(channel, indent=4))
					for permissions in channel.get("permission_overwrites"):
						print(json.dumps(permissions, indent=4))
						if permissions["id"] == interaction["member"]["user"]["id"] and permissions["allow"] == "554385280784":
							await session.delete(
								f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
								headers = DISCORD_HEADERS
							)
							return {
								"type": 4,
								"data": {
									"content": f"{EMOJIS['SUCCESS']} Ended the voice channel session.",
									"flags": 64
								}
							}
						else:
							continue
					
					return {
						"type": 4,
						"data": {
							"content": f"{EMOJIS['FAIL']} You don't have permission to delete this voice channel.",
							"flags": 64
						}
					}

		elif data.get("name") == "token" and data["options"][0]["name"] == "generate":
			async with aiohttp.ClientSession() as session:
				async with session.post(
					f"https://api.senarc.online/admin/token/create",
					headers = {
						"Authorisation": constants.get("API_TOKEN")
					},
					json = {
						"discord": {
							"id": interaction["member"]["user"]["id"],
							"username": interaction["member"]["user"]["username"],
							"discriminator": interaction["member"]["user"]["discriminator"],
						},
						"email": data["options"][0]["options"][0]["value"],
						"ip_type": data["options"][0]["options"][1]["value"]
					}
				) as response_:
					response = await response_.json()
					if response_.status == 400:
						return {
							"type": 4,
							"data": {
								"content": f"{EMOJIS['FAIL']} You already have a Senarc Token with this Discord or Email.",
								"flags": 64
							}
						}
					return {
						"type": 4,
						"data": {
							"content": f"{EMOJIS['SUCCESS']} Your token is `{response['token']}` activate it before use, and please keep it safe.",
							"flags": 64
						}
					}

		elif interaction.get("data").get("name") == "eval":
			return {
				"type": 9,
				"data": {
					"title": "Eval",
					"custom_id": "eval",
					"components": [
						{
							"type": 1,
							"components": [
								{
									"type": 4,
									"custom_id": "code",
									"label": "Code",
									"style": 2,
									"placeholder": "Your Python Code goes here.",
									"required": True
								}
							]
						}
					]
				}
			}

		elif interaction.get("data").get("name") == "modmail" and interaction.get("data").get("options")[0].get("name") == "create":
			# print(json.dumps(interaction, indent=4))
			# client = AsyncIOMotorClient(constants.get("MONGO_URL"))
			# collection = client["core"]["blacklists"]
			# if interaction["user"]["id"] in (await collection.find_one({"_id": "modmail"}))["users"]:
			# 	return {
			# 		"type": 4,
			# 		"data": {
			# 			"content": f"{EMOJIS['WARNING']} You are blacklisted from using this command.",
			# 			"flags": 64
			# 		}
			# 	}

			if (await ApplicationSyncManager.send_action_packet(
				{
					"action": 201,
					"data": {
						"member_id": interaction["user"]["id"]
					}
				}
			))["status"] == "failed":
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['WARNING']} Your DMs are already connected to the Modmail system.",
						"flags": 64
					}
				}

			if not interaction.get("guild_id") == None:
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['WARNING']} This interaction command is DM Only.",
						"flags": 64
					}
				}

			async with aiohttp.ClientSession() as session:
				OPTION_TO_TAG = {
					"moderation": "1047030629210005587",
					"suggestion": "1047030788685832243",
					"report": "1047030857128476694",
					"questions": "1047031376639164427",
					"other": "1047031455139758092"
				}
				async with session.post(
					f"{ENDPOINT_URL}/channels/{CHANNELS['MODMAIL_FORUM']}/threads",
					headers = DISCORD_HEADERS,
					json = {
						"name": f"{interaction['user']['username']}",
						"applied_tags": [OPTION_TO_TAG[interaction.get("data").get("options")[0].get("options")[0].get("value")]],
						"auto_archive_duration": 1440,
						"message": {
							"content": interaction['user']['id'],
							"embeds": [
								{
									"author": {
										"name": "Modmail",
										"icon_url": f"https://cdn.discordapp.com/avatars/{interaction['user']['id']}/{interaction['user']['avatar']}.png"
									},
									"color": 3158326,
									"description": f"**`{interaction['user']['username']}#{interaction['user']['discriminator']}` (`{interaction['user']['id']}`)** has created a modmail.\n\nYou may now start talking and interact with the user.",
									"footer": {
										"text": f"Senarc Core",
										"icon_url": "https://images-ext-2.discordapp.net/external/ww8h71y3iQC3iyNQ_y1Od1kh1AcDQUHIQ7ii3IBr-Xk/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/891952531926843402/e630b5d282b157a1d4b904f63add0d3f.png"
									},
									"timestamp": datetime.datetime.utcnow().isoformat()
								}
							]
						},
					}
				) as thread:
					thread = await thread.json()
					return {
						"type": 4,
						"data": {
							"embeds": [
								{
									"author": {
										"name": "Modmail System",
										"icon_url": "https://i.ibb.co/LhPgDhS/Cloud.png"
									},
									"color": 3158326,
									"description": "Your DMs have now been connected to Senarc's Modmail System.\nSenarc Staff members will get in touch with you shortly.\n\n*Please note that your conversation with us will be recorded for future referance, training purposes, and quality improvements.*",
									"footer": {
										"text": "Senarc Core",
										"icon_url": "https://images-ext-2.discordapp.net/external/ww8h71y3iQC3iyNQ_y1Od1kh1AcDQUHIQ7ii3IBr-Xk/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/891952531926843402/e630b5d282b157a1d4b904f63add0d3f.png"
									},
									"timestamp": datetime.datetime.utcnow().isoformat()
								},
							],
						}
					}

		elif interaction.get("data").get("name") == "modmail" and interaction.get("data").get("options")[0].get("name") == "close":
			if not interaction.get("guild_id") == None and not interaction.get("channel_id") == CHANNELS['MODMAIL_FORUM']:
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['WARNING']} This interaction command is DM Only.",
						"flags": 64
					}
				}

			if interaction.get("guild_id") == None:
				member_id = interaction['user']['id']
				interaction_type = 1

			else:
				member_id = interaction['channel_id']
				interaction_type = 2

			if (await ApplicationSyncManager.send_action_packet(
				{
					"action": 202,
					"data": {
						"type": interaction_type,
						"id": member_id
					}
				}
			))["status"] == "completed":
				return {
					"type": 4,
					"data": {
						{
							"author": {
								"name": "Modmail System",
								"icon_url": "https://i.ibb.co/LhPgDhS/Cloud.png"
							},
							"color": 3158326,
							"description": "Your DMs have been disconnected from Senarc's Modmail System.\nYour Messages will no longer be linked to any chat or logs.",
							"footer": {
								"text": "Senarc Core",
								"icon_url": "https://images-ext-2.discordapp.net/external/ww8h71y3iQC3iyNQ_y1Od1kh1AcDQUHIQ7ii3IBr-Xk/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/891952531926843402/e630b5d282b157a1d4b904f63add0d3f.png"
							},
							"timestamp": datetime.datetime.utcnow().isoformat()
						},
					}
				}

	elif interaction["type"] == 3:
		PING_ROLES = constants.get("PING_ROLES")
		payload = interaction["data"]
		if payload.get("custom_id") in PING_ROLES:
			async with aiohttp.ClientSession() as session:
				async with session.get(
					f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/members/{interaction['member']['user']['id']}",
					headers = DISCORD_HEADERS
				) as response:
					response = await response.json()
					if PING_ROLES[payload.get("custom_id")] in response.get("roles"):
						await session.delete(
							f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/members/{interaction['member']['user']['id']}/roles/{PING_ROLES[payload.get('custom_id')]}",
							headers = DISCORD_HEADERS
						)

						return {
							"type": 4,
							"data":{
								"content": f"{EMOJIS['SUCCESS']} `{payload.get('custom_id')}` role has been removed to your account.",
								"flags": 64
							}
						}

					else:
						await session.put(
							f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/members/{interaction['member']['user']['id']}/roles/{PING_ROLES[payload.get('custom_id')]}",
							headers = DISCORD_HEADERS
						)

						return {
							"type": 4,
							"data":{
								"content": f"{EMOJIS['SUCCESS']} `{payload.get('custom_id')}` role has been added to your account.",
								"flags": 64
							}
						}

		elif payload.get("custom_id") == "CLEAR_ALL":
			async with aiohttp.ClientSession() as session:
				for custom_id, _id in constants.get("PING_ROLES").items():
					await session.delete(
						f"{ENDPOINT_URL}/guilds/{Client.core_guild_id}/members/{interaction['member']['user']['id']}/roles/{_id}",
						headers = DISCORD_HEADERS
					)
			
			return {
				"type": 4,
				"data":{
					"content": f"{EMOJIS['SUCCESS']} Cleared all roles from your account.",
					"flags": 64
				}
			}

		elif payload.get("custom_id").startswith("delete_"):
			args = payload.get("custom_id").split("_")[1:]
			key = args[0] if not args[-1] == "message" else None
			deletion_token = args[1] if not args[-1] == "message" else None
			if interaction.get("member").get("user").get("id") == interaction.get("message").get("interaction").get("user").get("id"):	
				if not args[-1] == "message":
					async with aiohttp.ClientSession() as session:
						await session.delete(
							f"https://api.senarc.online/bin/{key}",
							headers = {
								"deletion_token": deletion_token
							}
						)
						await session.delete(
							f"{ENDPOINT_URL}/channels/{interaction.get('message').get('channel_id')}/messages/{interaction.get('message').get('id')}",
							headers = DISCORD_HEADERS
						)

						return {
							"type": 1
						}

				else:
					async with aiohttp.ClientSession() as session:
						await session.delete(
							f"{ENDPOINT_URL}/channels/{interaction.get('message').get('channel_id')}/messages/{interaction.get('message').get('id')}",
							headers = DISCORD_HEADERS
						)

						return {
							"type": 1
						}

			return {
				"type": 4,
				"data": {
					"content": f"{EMOJIS['FAIL']} Only the interaction author can delete this message.",
					"flags": 64
				}
			}

	elif interaction["type"] == 5:
		eval_code = {
			0: EMOJIS["SUCCESS"],
			1: EMOJIS["WARNING"]
		}
		payload = interaction["data"]
		if payload.get("custom_id") == "eval":
			code = payload.get("components")[0]["components"][0]["value"]
			if code == "":
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['FAIL']} You didn't provide any code to execute.",
						"flags": 64
					}
				}
			else:
				async with aiohttp.ClientSession() as session:
					if code.startswith("```py") and code.endswith("```"):
						code = (code[5:])[:3]
					elif code.startswith("```") and code.endswith("```"):
						code = (code[3:])[:3]

					async with session.post(
						"https://snekbox.senarc.online/eval",
						json = {
							"input": code
						}
					) as response:
						response = await response.json()
						output = response.get('stdout')
						returncode = response.get('returncode')
						output_ = output.split("\n")[:-1]
						modified = False
						count = 0
						_output = ""
						for line in output_:
							count += 1
							_output = _output + f"{(3 - len(str(count)))*'0'}{count} | {line}\n"

						if "```" in _output:
							async with session.post(
								"https://api.senarc.online/paste",
								json = {
									"title": "Snekbox Eval Output",
									"content": output,
									"description": code,
									"background_colour": "#1c1e26",
									"text_colour": "#dda487",
									"embed_colour": "#90B5F8"
								}
							) as paste:
								paste = await paste.json()
								full_output = paste.get("url")
								return {
									"type": 4,
									"data": {
										"content": f"{EMOJIS['WARNING']} Detected attempt to escape code block, output will not be sent in discord.",
										"components": [
											{
												"type": 1,
												"components": [
													{
														"type": 2,
														"label": "View Output",
														"style": 5,
														"url": paste.get("url")
													},
													{
														"type": 2,
														"label": "Delete",
														"style": 4,
														"custom_id": f"delete_{paste.get('key')}_{paste.get('deletion_token')}"
													}
												]
											}
										]
									}
								}

						if len(_output.split("\n")) > 20:
							_output = "\n".join(_output.split("\n")[:19])
							_output += "\n[...]"
							async with session.post(
								"https://api.senarc.online/paste",
								json = {
									"title": "Snekbox Eval Output",
									"content": output,
									"description": code,
									"background_colour": "#1c1e26",
									"text_colour": "#dda487",
									"embed_colour": "#90B5F8"
								}
							) as paste:
								paste = await paste.json()
								full_output = paste.get("url")
								modified = True

						elif len(output) > 1500 and not modified:
							_output = _output[:1497]
							_output += "..."
							async with session.post(
								"https://api.senarc.online/paste",
								json = {
									"title": "Snekbox Eval Output",
									"content": output,
									"description": code,
									"background_colour": "#1c1e26",
									"text_colour": "#dda487",
									"embed_colour": "#90B5F8"
								}
							) as paste:
								paste = await paste.json()
								full_output = paste.get("url")
								modified = True

						if _output.replace("\n", "") == "":
							_output = "[No output]"

						if returncode == 0:
							message = f"{eval_code[0]} Successfully executed code."

						else:
							message = f"{eval_code[1]} Code execution returned code `{returncode}`."

						if modified:
							return {
								"type": 4,
								"data": {
									"content": f"{message}\n\n```py\n{_output}```",
									"components": [
										{
											"type": 1,
											"components": [
												{
													"type": 2,
													"label": "Full Output",
													"style": 5,
													"url": full_output
												},
												{
													"type": 2,
													"label": "Delete",
													"style": 4,
													"custom_id": f"delete_{paste.get('key')}_{paste.get('deletion_token')}"
												}
											]
										}
									]
								}
							}

						return {
							"type": 4,
							"data": {
								"content": f"{message}\n\n```py\n{_output}```",
								"components": [
									{
										"type": 1,
										"components": [
											{
												"type": 2,
												"label": "Delete",
												"style": 4,
												"custom_id": "delete_message"
											}
										]
									}
								]
							}
						}

@Router.get("/register")
async def register_call(request: Request):

	guild_commands = [
		{
			"name": "voice",
			"description": "Voice Channel controller.",
			"options": [
				{
					"name": "create",
					"type": 1,
					"description": "Create a voice channel."
				},
				{
					"name": "permit",
					"type": 2,
					"description": "Permit a user to join a voice channel.",
					"options": [
						{
							"name": "approve",
							"description": "Approve a user to join a voice channel.",
							"type": 1,
							"options": [
								{
									"name": "user",
									"description": "The user to approve the permit to join the voice channel.",
									"type": 6,
									"required": True
								}
							]
						},
						{
							"name": "deny",
							"description": "Deny a user to join a voice channel.",
							"type": 1,
							"options": [
								{
									"name": "user",
									"description": "The user to remove the permit of the voice channel.",
									"type": 6,
									"required": True
								}
							]
						}
					]
				},
				{
					"name": "end",
					"type": 1,
					"description": "End your voice channel."
				}
			]
		},
		{
			"name": "eval",
			"type": 1,
			"description": "Evaluate Python code."
		},
		{
			"name": "token",
			"description": "Manage your token.",
			"options": [
				{
					"name": "generate",
					"type": 1,
					"description": "Generate a new token.",
					"options": [
						{
							"name": "email",
							"description": "Your email connected to Discord.",
							"type": 3,
							"required": True
						},
						{
							"name": "type",
							"description": "Do you have a Dynamic or Static IP?",
							"type": 3,
							"required": True,
							"choices": [
								{
									"name": "Dynamic IP",
									"value": "dynamic"
								},
								{
									"name": "Static IP",
									"value": "static"
								}
							]
						}
					]
				}
			]
		}
	]

	global_commands = [
		{
			"name": "modmail",
			"description": "Modmail Ticket management.",
			"options": [
				{
					"name": "create",
					"type": 1,
					"description": "Create a modmail thread. (DM Only)",
					"options": [
						{
							"name": "topic",
							"description": "Pick the topic you're opening a Modmail about.",
							"type": 3,
							"required": True,
							"choices": [
								{
									"name": "Moderation",
									"value": "moderation"
								},
								{
									"name": "Suggestion",
									"value": "suggestion"
								},
								{
									"name": "Report/Bug",
									"value": "report"
								},
								{
									"name": "Question",
									"value": "question"
								},
								{
									"name": "Other",
									"value": "other"
								}
							]
						}
					]
				},
				{
					"name": "close",
					"type": 1,
					"description": "Close a modmail thread. (DM Only)",
					"options": [
						{
							"name": "reason",
							"description": "The reason for closing the modmail thread.",
							"type": 3,
							"required": False
						}
					]
				}
			]
		}
	]

	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(
				f"{ENDPOINT_URL}/applications/{Client.id}/commands",
				headers = DISCORD_HEADERS
			) as response_:
				for command in (await response_.json()):
					await session.delete(
						f"{ENDPOINT_URL}/applications/{Client.id}/commands/{command['id']}",
						headers = DISCORD_HEADERS
					)
					
			async with session.get(
				f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands",
				headers = DISCORD_HEADERS
			) as response_:
				for command in (await response_.json()):
					await session.delete(
						f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands/{command['id']}",
						headers = DISCORD_HEADERS
					)

			for command in guild_commands:
				async with session.post(
					f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands",
					headers = DISCORD_HEADERS,
					json = command
				) as response_:
					print(await response_.json())

			for command in global_commands:
				async with session.post(
					f"{ENDPOINT_URL}/applications/{Client.id}/commands",
					headers = DISCORD_HEADERS,
					json = command
				) as response_:
					print(await response_.json())
	except:
		return {
			"success": False
		}, 501
	return {
		"success": True
	}
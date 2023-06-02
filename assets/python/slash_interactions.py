import os
import sys
import json
import aiohttp
import datetime
import traceback

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from motor.motor_asyncio import AsyncIOMotorClient

from fastapi import APIRouter
from fastapi import Request

from .internal import Internal, ApplicationSyncManager
from .type import Modmail, ActionPacket

internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CORE_GUILD_ID",
	"CLIENT_PUBLIC_KEY",
	"API_TOKEN",
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
UPLOAD_ENDPOINT = f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands"
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

	if interaction["type"] == 1:
		return {
			"type": 1
		}

	if interaction["type"] == 2:
		data = interaction.get("data")
		if data.get("name") == "token" and data["options"][0]["name"] == "generate":
			async with aiohttp.ClientSession() as session:
				async with session.post(
					f"https://api.senarc.net/admin/token/create",
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
			if (await ApplicationSyncManager.send_action_packet(
				{
					"interaction": ActionPacket.CALLBACK,
					"action": Modmail.Action.CHECK_THREAD_EXISTANCE,
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
				interaction_type = Modmail.InteractionType.DM

			else:
				member_id = interaction['channel_id']
				interaction_type = Modmail.InteractionType.THREAD

			if (await ApplicationSyncManager.send_action_packet(
				{
					"interaction": ActionPacket.CALLBACK,
					"action": Modmail.Action.THREAD_DELETE,
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

		elif interaction.get("data").get("name") == "solve":
			if interaction.get("channel_id") != CHANNELS['HELP_FORUM']:
				return {
					"type": 4,
					"data": {
						"content": f"{EMOJIS['WARNING']} This interaction command only works on help threads.",
						"flags": 64
					}
				}

			return {
				"type": 4,
				"data": {
					"content": f"{EMOJIS['WARNING']} Are you sure you want to mark this thread as solved?",
					"embeds": [
						{
							"author": {
								"name": "Mark Thread as Solved",
								"icon_url": "https://cdn.discordapp.com/emojis/1035574699566051358.webp?size=512&quality=lossless"
							},
							"color": 2829617,
							"description": "This will mark the thread as solved, and lock the thread preventing more messages being sent unless re-opened by a moderator.",
							"footer": {
								"text": "Senarc Core",
								"icon_url": "https://images-ext-2.discordapp.net/external/ww8h71y3iQC3iyNQ_y1Od1kh1AcDQUHIQ7ii3IBr-Xk/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/891952531926843402/e630b5d282b157a1d4b904f63add0d3f.png"
							},
							"timestamp": datetime.datetime.utcnow().isoformat()
						}
					],
					"flags": 64,
					"components": [
						{
							"type": 1,
							"components": [
								{
									"type": 2,
									"style": 3,
									"label": "Yes",
									"custom_id": "solve_confirm"
								},
								{
									"type": 2,
									"style": 4,
									"label": "No",
									"custom_id": "solve_cancel"
								}
							]
						}
					]
				}
			}

		elif interaction.get("data").get("name") == "mta" and interaction.get("data").get("options")[0].get("name") == "user":
			if interaction.get("data").get("options")[0].get("options")[0].get("name") == "user":
				async with aiohttp.ClientSession() as session:
					async with session.get(f"https://api.senarc.net/mta/id/{interaction.get('data').get('options')[0].get('options')[0].get('value')}") as response:
						user = await response.json()
						if response.status == 404:
							return {
								"type": 4,
								"data": {
									"embeds": [
										{
											"author": {
												"name": "No MTA Certificates",
												"icon_url": f"https://cdn.discordapp.com/avatars/{interaction.get('member').get('user').get('id')}/{interaction.get('member').get('user').get('avatar')}.webp?size=1024"
											},
											"color": 2829617,
											"description": f"No Certificate was found for `{interaction.get('data').get('options')[0].get('options')[0].get('value')}`",
											"footer": {
												"text": "Senarc MTA",
												"icon_url": "https://cdn.discordapp.com/avatars/891952531926843402/3c6199f323021fc89955632314b09c95.webp?size=128"
											}
										}
									]
								}
							}

						elif response.status == 200:
							if user.get("linked_guild") is None:
								return {
									"type": 4,
									"data": {
										"embeds": [
											{
												"author": {
													"name": "MTA Certificate",
													"icon_url": f"{user.get('icon_url')}"
												},
												"color": 2829617,
												"fields": [
													{
														"name": "> User",
														"value": f"<@!{user['_id']}> (`{user['_id']}`)",
														"inline": True
													},
													{
														"name": "> Token",
														"value": f"`{user['token']}`",
														"inline": True
													},
													{
														"name": "> Expiry",
														"value": f"`{user['expires_at']}`",
														"inline": False
													},
													{
														"name": "> Status",
														"value": f"`{user['status']}`",
														"inline": True
													}
												],
												"footer": {
													"text": f"Since {user['created_at']}",
													"icon_url": f"{user['icon_url']}"
												}
											}
										]
									}
								}
							return {
								"type": 4,
								"data": {
									"embeds": [
										{
											"author": {
												"name": "MTA Certificate",
												"icon_url": f"{user['icon_url']}"
											},
											"color": 2829617,
											"description": "",
											"fields": [
												{
													"name": "User",
													"value": f"<@!{user['_id']}>",
													"inline": True
												},
												{
													"name": "Token",
													"value": f"`{user['token']}`",
													"inline": True
												},
												{
													"name": "Status",
													"value": f"`{user['status']}`",
													"inline": True
												},
												{
													"name": "Linked Guild",
													"value": f"{user.get('linked_guild').get('name')} (`{user.get('linked_guild').get('id')}`)",
													"inline": False
												},
												{
													"name": "Guild Owner",
													"value": f"<@!{user.get('linked_guild').get('guild_owner')['id']}> (`{user.get('linked_guild').get('guild_owner')['id']}`)",
													"inline": True
												},
												{
													"name": "Expiry",
													"value": f"<t:{user['expires_at']}:R>",
													"inline": False
												},
											],
											"footer": {
												"text": f"Since",
												"icon_url": f"{user['icon_url']}"
											},
											"timestamp": datetime.datetime.fromtimestamp(user['created_at']).isoformat()
										}
									]
								}
							}

		elif interaction.get("data").get("name") == "mta" and interaction.get("data").get("options")[0].get("name") == "guild":
			async with aiohttp.ClientSession() as session:
				async with session.get(f"https://api.senarc.net/mta/id/{interaction.get('data').get('options')[0].get('options')[0].get('value')}") as response:
					guild = await response.json()
					if response.status == 404:
						return {
							"type": 4,
							"data": {
								"embeds": [
									{
										"author": {
											"name": "No MTA Certificates",
											"icon_url": f"https://cdn.discordapp.com/avatars/{interaction.get('member').get('user').get('id')}/{interaction.get('member').get('user').get('avatar')}.webp?size=1024"
										},
										"color": 2829617,
										"description": f"No Certificate was found for `{interaction.get('data').get('options')[0].get('options')[0].get('value')}`",
										"footer": {
											"text": "Senarc MTA",
											"icon_url": "https://cdn.discordapp.com/avatars/891952531926843402/3c6199f323021fc89955632314b09c95.webp?size=128"
										}
									}
								]
							}
						}

					elif response.status == 200:
						return {
								"type": 4,
								"data": {
									"embeds": [
										{
											"author": {
												"name": "MTA Certificate",
												"icon_url": f"{guild['icon_url']}"
											},
											"color": 2829617,
											"fields": [
												{
													"name": "> Guild",
													"value": f"{guild['guild_name']} (`{guild['guild_id']}`)",
													"inline": True
												},
												{
													"name": "> Guild Owner",
													"value": f"<@!{guild['guild_owner']['id']}> (`{guild['guild_owner']['id']}`)",
													"inline": True
												},
												{
													"name": "> Token",
													"value": f"`{guild['token']}`",
													"inline": True
												},
												{
													"name": "> Expiry",
													"value": f"`{guild['expires_at']}`",
													"inline": False
												},
												{
													"name": "> Status",
													"value": f"`{guild['status']}`",
													"inline": True
												}
											],
											"footer": {
												"text": f"Since {guild['created_at']}",
												"icon_url": f"{guild['icon_url']}"
											}
										}
									]
								}
							}

		elif interaction.get("data").get("name") == "mta" and interaction.get("data").get("options")[0].get("name") == "token":
			async with aiohttp.ClientSession() as session:
				async with session.get(f"https://api.senarc.net/mta/token/{interaction.get('data').get('options')[0].get('options')[0].get('value')}") as response:
					certificate = await response.json()
					if response.status == 404:
						return {
							"type": 4,
							"data": {
								"embeds": [
									{
										"author": {
											"name": "No MTA Certificates",
											"icon_url": f"https://cdn.discordapp.com/avatars/{interaction.get('member').get('user').get('id')}/{interaction.get('member').get('user').get('avatar')}.webp?size=1024"
										},
										"color": 2829617,
										"description": f"No Certificate was found for `{interaction.get('data').get('options')[0].get('options')[0].get('value')}`",
										"footer": {
											"text": "Senarc MTA",
											"icon_url": "https://cdn.discordapp.com/avatars/891952531926843402/3c6199f323021fc89955632314b09c95.webp?size=128"
										}
									}
								]
							}
						}

					elif response.status == 200:
						if certificate.get("type") == "user":
							if certificate.get("linked_guild") is None:
								return {
									"type": 4,
									"data": {
										"embeds": [
											{
												"author": {
													"name": "MTA Certificate",
													"icon_url": f"{certificate.get('icon_url')}"
												},
												"color": 2829617,
												"fields": [
													{
														"name": "> User",
														"value": f"<@!{certificate['_id']}> (`{certificate['_id']}`)",
														"inline": True
													},
													{
														"name": "> Token",
														"value": f"`{certificate['token']}`",
														"inline": True
													},
													{
														"name": "> Expiry",
														"value": f"`{certificate['expires_at']}`",
														"inline": False
													},
													{
														"name": "> Status",
														"value": f"`{certificate['status']}`",
														"inline": True
													}
												],
												"footer": {
													"text": f"Since {certificate['created_at']}",
													"icon_url": f"{certificate['icon_url']}"
												}
											}
										]
									}
								}
							return {
								"type": 4,
								"data": {
									"embeds": [
										{
											"author": {
												"name": "MTA Certificate",
												"icon_url": f"{interaction.get('data').get('author').get('avatar_url')}"
											},
											"color": 2829617,
											"fields": [
												{
													"name": "> User",
													"value": f"<@!{certificate['_id']}> (`{certificate['_id']}`)",
													"inline": True
												},
												{
													"name": "> Token",
													"value": f"`{certificate['token']}`",
													"inline": True
												},
												{
													"name": "> Linked Guild",
													"value": f"{certificate.get('linked_guild').get('guild_name')} (`{certificate.get('linked_guild').get('guild_id')}`)",
													"inline": False
												},
												{
													"name": "> Guild Owner",
													"value": f"<@!{certificate.get('linked_guild').get('guild_owner').get('id')}> (`{certificate.get('linked_guild').get('guild_owner').get('id')}`)",
													"inline": True
												},
												{
													"name": "> Expiry",
													"value": f"<t:{certificate['expires_at']}:R>",
													"inline": False
												},
												{
													"name": "> Status",
													"value": f"`{certificate['status']}`",
													"inline": True
												}
											],
											"footer": {
												"text": f"Since {certificate['created_at']}",
												"icon_url": f"{certificate['icon_url']}"
											}
										}
									]
								}
							}
						elif certificate.get("type") == "guild":
							return {
								"type": 4,
								"data": {
									"embeds": [
										{
											"author": {
												"name": "MTA Certificate",
												"icon_url": f"{certificate.get('icon_url')}"
											},
											"color": 2829617,
											"fields": [
												{
													"name": "> Guild",
													"value": f"{certificate['guild_name']} (`{certificate['guild_id']}`)",
													"inline": True
												},
												{
													"name": "> Guild Owner",
													"value": f"<@!{certificate['guild_owner']['id']}> (`{certificate['guild_owner']['id']}`)",
													"inline": True
												},
												{
													"name": "> Token",
													"value": f"`{certificate['token']}`",
													"inline": True
												},
												{
													"name": "> Expiry",
													"value": f"`{certificate['expires_at']}`",
													"inline": False
												},
												{
													"name": "> Status",
													"value": f"`{certificate['status']}`",
													"inline": True
												}
											],
											"footer": {
												"text": f"Since {certificate['created_at']}",
												"icon_url": f"{certificate['icon_url']}"
											}
										}
									]
								}
							}

	elif interaction["type"] == 3:
		if payload.get("custom_id") == "solve_confirm":
			async with aiohttp.ClientSession() as session:
				await session.patch(
					f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
					headers = DISCORD_HEADERS,
					json = {
						"locked": True,
						"archived": True
					}
				)
				return {
					"type": 7,
					"data": {
						"content": f"{EMOJIS['SUCCESS']} Thread marked as solved.",
						"flags": 64
					}
				}
			
		elif payload.get("custom_id") == "solve_cancel":
			return {
				"type": 7,
				"data": {
					"content": f"{EMOJIS['WARNING']} Thread was not marked as solved.",
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
							f"https://api.senarc.net/bin/{key}",
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
						"https://snekbox.senarc.net/eval",
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
								"https://api.senarc.net/paste",
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
								"https://api.senarc.net/paste",
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
								"https://api.senarc.net/paste",
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
		},
		{
			"name": "eval",
			"type": 1,
			"description": "Evaluate Python code."
		},
		{
			"name": "solve",
			"type": 1,
			"description": "Mark a help thread as solved."
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
		},
		{
			"name": "mta",
			"description": "MTA Info.",
			"options": [
				{
					"name": "user",
					"type": 1,
					"description": "Check for user's MTA certificate.",
					"options": [
						{
							"name": "user",
							"description": "The user you want to check for.",
							"type": 6,
							"required": False
						}
					]
				},
				{
					"name": "guild",
					"type": 1,
					"description": "Check for guild's MTA certificate.",
					"options": [
						{
							"name": "guild",
							"description": "The guild id you want to check for.",
							"type": 3,
							"required": False
						}
					]
				},
				{
					"name": "token",
					"type": 1,
					"description": "Look up Tokens",
					"options": [
						{
							"name": "token",
							"description": "Certificate Token",
							"type": 3,
							"required": True
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
				response = await response_.json()
				for global_command in global_commands:
					if global_command["name"] not in [
						response_command["name"]
						for response_command in response
					]:
						await session.post(
							f"{ENDPOINT_URL}/applications/{Client.id}/commands",
							headers = DISCORD_HEADERS,
							json = global_command
						)
						continue
					for command in response:
						print(command, global_command)
						async with session.get(
							f"{ENDPOINT_URL}/applications/{Client.id}/commands/{command['id']}",
							headers = DISCORD_HEADERS
						) as command_payload:
							command_payload = await command_payload.json()
							if command["name"] not in [
								global_command_entries["name"]
								for global_command_entries in global_commands
							]:
								await session.delete(
									f"{ENDPOINT_URL}/applications/{Client.id}/commands/{command_payload['id']}",
									headers = DISCORD_HEADERS
								)
							else:
								await session.patch(
									f"{ENDPOINT_URL}/applications/{Client.id}/commands/{command_payload['id']}",
									headers = DISCORD_HEADERS,
									json = command
								)

		async with aiohttp.ClientSession() as session:
			async with session.get(
				f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands",
				headers = DISCORD_HEADERS
			) as response_:
				response = await response_.json()
				for guild_command in guild_commands:
					if guild_command["name"] not in [
						response_command["name"]
						for response_command in response
					]:
						await session.post(
							f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands",
							headers = DISCORD_HEADERS,
							json = guild_command
						)
						continue
					for command in response:
						async with session.get(
							f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands/{command['id']}",
							headers = DISCORD_HEADERS
						) as command_payload:
							command_payload = await command_payload.json()
							if command["name"] not in command_payload["name"]:
								await session.delete(
									f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands/{command['id']}",
									headers = DISCORD_HEADERS
								)
							else:
								await session.patch(
									f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands/{command['id']}",
									headers = DISCORD_HEADERS,
									json = command
								)

			# async with session.get(
			# 	f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands",
			# 	headers = DISCORD_HEADERS
			# ) as response_:
			# 	for command in (await response_.json()):
			# 		await session.delete(
			# 			f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands/{command['id']}",
			# 			headers = DISCORD_HEADERS
			# 		)

			# for command in guild_commands:
			# 	async with session.post(
			# 		f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{constants.get('CORE_GUILD_ID')}/commands",
			# 		headers = DISCORD_HEADERS,
			# 		json = command
			# 	) as response_:
			# 		print(await response_.json())

			# for command in global_commands:
			# 	async with session.post(
			# 		f"{ENDPOINT_URL}/applications/{Client.id}/commands",
			# 		headers = DISCORD_HEADERS,
			# 		json = command
			# 	) as response_:
			# 		print(await response_.json())
	except Exception as e:
		# Print Traceback
		traceback.print_exc()
		# Return Error
		return f"{e}", 501

	return {
		"success": True
	}

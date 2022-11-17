import os
import sys
import json
import aiohttp

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from fastapi import APIRouter
from fastapi import Request

from assets.python.internal import Internal, ApplicationSyncManager

internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
constants.fetch("CLIENT_PUBLIC_KEY")
constants.fetch("PING_ROLES")
constants.fetch("EMOJIS")
constants.fetch("CHANNELS")
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

async def asm_ensure_running() -> bool:
	if not ApplicationSyncManager.is_running:
		await ApplicationSyncManager.start()
		return False

	else:
		return True

@Router.on_event("startup")
async def startup() -> None:
	await asm_ensure_running()

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

		elif interaction.get("data").get("name") == "eval":
			print("eval")
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

	elif interaction["type"] == 5:
		eval_code = {
			0: EMOJIS["SUCCESS"],
			1: EMOJIS["FAIL"],
			2: EMOJIS["WARNING"]
		}
		payload = interaction["data"]
		if payload.get("custom_id") == "eval":
			code = payload.get("components")[0]["value"]
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
							"input": code,
						}
					):
						response = await response.json()
						output = response.get('stdout')
						returncode = response.get('returncode')
						output_ = output.split("\n")
						modified = False
						count = 0
						_output = ""
						for line in output_:
							count += 1
							_output = _output + f"{(3 - len(str(count)))*'0'}{count} | {line}\n"

						if len(_output) > 20:
							_output = "\n".join(_output.split("\n")[:19])
							_output += "\n[...]"
							async with session.post(
								"https://api.senarc.online/paste",
								json = {
									"title": "Snekbox Eval Output",
									"content": output,
									"description": code,
								}
							):
								response = await response.json()
								full_output = response.get("url")
								modified = True

						elif len(output) > 500 and not modified:
							_output = _output[:497]
							_output += "..."
							async with session.post(
								"https://api.senarc.online/paste",
								json = {
									"title": "Snekbox Eval Output",
									"content": output,
									"description": code,
								}
							):
								response = await response.json()
								full_output = response.get("url")
								modified = True

						if _output.replace("\n", "") == "":
							_output = "[No output]"
							returncode = 2

						if returncode == 0:
							message = "Successfully executed code."

						elif returncode == 1:
							message = "Code execution was successful, but no output was returned."

						elif returncode == 2:
							message = "Code execution failed."

						if modified:
							return {
								"type": 4,
								"data": {
									"content": f"{eval_code[returncode]} {message}\n\n```py\n{_output}```",
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
											"custom_id": f"delete_{response.get('key')}_{response.get('deletion_token')}"
										}
									]
								}
							}

						return {
							"type": 4,
							"data": {
								"content": f"{eval_code[returncode]} {message}\n\n```py\n{_output}```",
								"flags": 64
							}
						}

@Router.get("/register")
async def register_call(request: Request):

	commands = [
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

			for command in commands:
				async with session.post(
					f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands",
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
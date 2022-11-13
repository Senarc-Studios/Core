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

@Router.get("/register")
async def register_call(request: Request):
	admin = request.headers.get("Authorisation")

	if admin not in internal.Dynamic.fetch("ADMIN_TOKENS"):
		return 'invalid admin verification', 401

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
			"name": "token",
			"options": []
		},
		{
			"name": "generate-token",
			"description": "Generate Senarc API Token."
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
					return await response_.json()
	except:
		return {
			"success": False
		}, 501
	return {
		"success": True
	}
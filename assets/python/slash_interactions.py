import os
import sys
import json
import aiohttp

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from fastapi import APIRouter
from fastapi import Request

from assets.python.internal import Internal

internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
Client = internal.Client(constants)

Router = APIRouter(
	prefix="/discord"
)
ENDPOINT_URL = "https://discord.com/api/v10"
UPLOAD_ENDPOINT = f"{ENDPOINT_URL}/applications/{Client.id}/guilds/{Client.core_guild_id}/commands"
DISCORD_HEADERS = {
	"Authorization": f"Bot {Client.token}",
	"Content-Type": "application/json"
}
BUTTON_ROLE_ID_MAP = {
	"role_ann": "1015551523771654184",
	"role_eve": "1015551585897689158",
	"role_qot": "1015618714713985175"
}

@Router.post("/interaction")
async def interaction_handler(request: Request):
	interaction = await request.json()
	PUBLIC_KEY = constants.fetch("CLIENT_PUBLIC_KEY")

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
			if not interaction.get("channel_id") == "1009722821364166706":
				return {
					"type": 4,
					"data": {
						"content": "<:forbidden:890082794112446548> You can only create a voice channel in <#1009722821364166706>.",
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
						print(json.dumps(guild_channels, indent = 4))
						for channel in guild_channels:
							if channel.get("parent_id") == "1009722813327867955":
								for permissions in channel.get("permission_overwrites"):
									if permissions["id"] == interaction["member"]["user"]["id"] and permissions["allow"] == "554385280784":
										return {
											"type": 4,
											"data": {
												"content": "<:forbidden:890082794112446548> You already have a voice channel.",
												"flags": 64
											}
										}

									else:
										continue

							else:
								continue

						async with session.post(
							f"{ENDPOINT_URL}/guilds/886543799843688498/channels",
							headers=DISCORD_HEADERS,
							json={
								"name": f"{interaction['member']['user']['username']}'s VC",
								"type": 2,
								"parent_id": "1009722813327867955",
								"permission_overwrites": [
									{
										"id": interaction["member"]["user"]["id"],
										"type": 1,
										"allow": 554385280784
									},
									{
										"id": "886543799843688498",
										"type": 0,
										"deny": 1024
									}
								]
							}
						) as resp:
							return {
								"type": 4,
								"data": {
									"content": f"<:success:890082793235816449> Created a voice channel: <#{(await resp.json())['id']}>",
									"flags": 64
								}
							}
		
		elif data.get("name") == "voice" and data["options"][0]["name"] == "permit":
			sub_action = data["options"][0]["options"][0]
			if sub_action["name"] == "approve":
				async with aiohttp.ClientSession() as session:
					async with session.patch(
						f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
						headers = DISCORD_HEADERS,
						json = {
							"permission_overwrites": [
								{
									"id": sub_action["options"][0]["value"],
									"type": 1,
									"allow": 549792517632
								}
							]
						}
					) as resp:
						return {
							"type": 4,
							"data": {
								"content": f"<:success:890082793235816449> Added <@{sub_action['options'][0]['value']}> to the voice channel.",
								"flags": 64
							}
						}
			
			elif sub_action["name"] == "deny":
				async with aiohttp.ClientSession() as session:
					async with session.patch(
						f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
						headers = DISCORD_HEADERS,
						json = {
							"permission_overwrites": [
								{
									"id": sub_action["options"][0]["value"],
									"type": 1,
									"allow": 0,
									"deny": 1024,
								}
							]
						}
					) as resp:
						return {
							"type": 4,
							"data": {
								"content": f"<:success:890082793235816449> Removed <@{sub_action['options'][0]['value']}> from the voice channel.",
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
					for permissions in channel.get("permission_overwrites"):
						if permissions["id"] == interaction["member"]["user"]["id"] and permissions["allow"] == "554385280784":
							await session.delete(
								f"{ENDPOINT_URL}/channels/{interaction['channel_id']}",
								headers = DISCORD_HEADERS
							)
							return {
								"type": 4,
								"data": {
									"content": f"<:success:890082793235816449> Ended the voice channel session.",
									"flags": 64
								}
							}
						else:
							continue
					
					return {
						"type": 4,
						"data": {
							"content": "<:forbidden:890082794112446548> You don't have permission to delete this voice channel.",
							"flags": 64
						}
					}

	elif interaction["type"] == 3:
		payload = interaction["data"]
		if payload.get("data")["custom_id"] in BUTTON_ROLE_ID_MAP:
			async with aiohttp.ClientSession() as session:
				async with session.get(
					f"{ENDPOINT_URL}/guilds/886543799843688498/members/{interaction['member']['user']['id']}",
					headers = DISCORD_HEADERS
				) as response:
					if BUTTON_ROLE_ID_MAP[payload.get("data")["custom_id"]] in response.get("roles"):
						await session.delete(
							f"{ENDPOINT_URL}/guilds/886543799843688498/members/{interaction['member']['user']['id']}/roles/{BUTTON_ROLE_ID_MAP[payload.get('data')['custom_id']]}",
							headers = DISCORD_HEADERS
						)

					else:
						await session.put(
							f"{ENDPOINT_URL}/guilds/886543799843688498/members/{interaction['member']['user']['id']}/roles/{BUTTON_ROLE_ID_MAP[payload.get('data')['custom_id']]}",
							headers = DISCORD_HEADERS
						)
			
			return {
				"type": 1
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
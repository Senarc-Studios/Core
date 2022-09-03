import os
import sys

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
	"Authorization": f"Bot {Client.token}"
}
BUTTON_ROLE_ID_MAP = {
	"role_ann": "1015551523771654184",
	"role_eve": "1015551585897689158",
	"role_qot": "1015618714713985175"
}

@Router.post("/interaction")
async def interaction_handler(request):
	interaction = await request.json()
	PUBLIC_KEY = '857a7a80ac7bcb00814d54af3cfce9276a1cff9fa0dd240af4fc6ae94294a0a6'

	verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

	signature = request.headers.get("X-Signature-Ed25519")
	timestamp = request.headers.get("X-Signature-Timestamp")
	body = request.data.decode("utf-8")

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
		if data.get("name") == "voice" and data["options"]["name"] == "create":
			if not data.get("channel_id") == "1009722821364166706":
				return {
					"type": 4,
					"data": {
						"content": "You can only create a voice channel in <#1009722821364166706>.",
						"flags": 6
					}
				}

			else:
				async with aiohttp.ClientSession() as session:
					async with session.post(
						f"{ENDPOINT_URL}/guilds/886543799843688498/channels",
						headers=DISCORD_HEADERS,
						json={
							"name": f"{interaction['member']['user']['username']}'s Voice Channel",
							"type": 2,
							"parent_id": "1009722813327867955"
						}
					) as resp:
						return {
							"type": 4,
							"data": {
								"content": f"Created a voice channel: <#{(await resp.json())['id']}>",
								"flags": 6
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
			"type": 2,
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
			for command in commands:
				async with session.put(
					ENDPOINT_URL,
					headers = DISCORD_HEADERS,
					json = command
				) as response:
					return await response.text()
	except:
		return {
			"success": False
		}
	return {
		"success": True
	}
import os
import sys

import aiohttp

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from fastapi import APIRouter
from fastapi import Request

# Import global_func from 3 directories up
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

Router = APIRouter(
	prefix="/discord"
)
ENDPOINT_URL = f"https://discord.com/api/v10/applications/{Router.Internal.Client.id}/guilds/{Router.Internal.Client.core_guild_id}/commands"
DISCORD_HEADERS = {
	"Authorization": f"Bot {Router.Internal.Client.token}"
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
		...

@Router.get("/register")
async def register_call(request: Request):
	admin = request.headers.get("Authorisation")

	if admin not in Router.Internal.Dynamic.fetch("ADMIN_TOKENS"):
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
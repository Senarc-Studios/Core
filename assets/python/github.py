import os
import json
import datetime
import asyncio

from fastapi import APIRouter
from fastapi import Request

from assets.python.internal import Internal

Router = APIRouter(
	"/github"
)
internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
constants.fetch("TOKEN")

@Router.post("/updates", include_in_schema = False)
async def git_updates(request: Request):
	commit = await request.json()
	count = 0
	commit_string = ""

	for commit_ in commit['commits']:
		count = count + 1

		if count == 5:
			commit_string = commit_string + "..."
			break

		if len(str(commit_['message'])) > 50:
			commit_['message'] = commit_['message'][:47] + "..."
		
		commit_string = commit_string + f"<:Dot:1038764950249807953> [`{commit['after'][:7]}`]({commit_['url']}) {commit_['message']} - [`{commit_['author']['name']}`](https://github.com/{commit_['author']['username']})\n"

	commit_heading = (
		"[ " +
		f"{commit['repository']['name']}" +
		" | " +
		f"{commit['repository']['master_branch']}" +
		f" ]  {len(commit['commits'])} Commits"
	) if len(commit['commits']) > 1 else (
		"[ " +
		f"{commit['repository']['name']}" +
		" | " +
		f"{commit['repository']['master_branch']}" +
		" ]"
	)
	payload = {
		"embeds": [
			{
				"title": commit_heading,
				"description": commit_string,
				"color": 0x91B6F7,
				"url": commit['compare'],
				"timestamp": datetime.datetime.utcnow().isoformat(),
				"author": {
					"name": commit['repository']['name'],
					"url": commit['repository']['url'],
					"icon_url": commit['repository']['owner']['avatar_url']
				},
				"footer": {
					"text": f"Senarc Core",
					"icon_url": "https://images-ext-1.discordapp.net/external/JLdEGrbDlsR6UPBiFvqjkB_EjbsQ7FqNYO6lmDLTO3g/https/i.ibb.co/DVRvMs4/image.png"
				}
			}
		]
	}

	async with asyncio.ClientSession() as session:
		await session.post(
			f"https://discord.com/api/v10/channels/1009722826208579634/messages",
			headers = {
				"Authorization": f"Bot {constants.get('TOKEN')}"
			},
			json = payload
		)
	return "ok", 200
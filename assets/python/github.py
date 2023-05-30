import datetime
import aiohttp

from fastapi import APIRouter
from fastapi import Request

from assets.python.internal import Internal

Router = APIRouter(
	prefix = "/github"
)
internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
constants.fetch("CLIENT_TOKEN")

@Router.post("/updates", include_in_schema = False)
async def git_updates(request: Request):
	commit = await request.json()
	count = 0
	commit_string = ""

	for commit_ in commit['commits']:
		count = count + 1

		if count == 20:
			commit_string = commit_string + "..."
			break

		if len(str(commit_['message'])) > 50:
			backticks: int = commit_["message"].count("`")
			commit_['message'] = commit_['message'][:47] + "..."
			commit_['message'] = commit_['message'] + "`" if backticks > commit_["message"].count("`") else commit_['message']

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
					"name": commit['sender']['login'],
					"url": commit['sender']['html_url'],
					"icon_url": commit['sender']['avatar_url']
				},
				"footer": {
					"text": f"Senarc Core",
					"icon_url": "https://cdn.discordapp.com/app-icons/891952531926843402/3c6199f323021fc89955632314b09c95?size=512"
				}
			}
		]
	}

	async with aiohttp.ClientSession() as session:
		await session.post(
			f"https://discord.com/api/v10/channels/1009722826208579634/messages",
			headers = {
				"Authorization": f"Bot {constants.get('CLIENT_TOKEN')}"
			},
			json = payload
		)
	return "ok", 200
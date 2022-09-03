import os

from assets.python.internal import Internal

import uvicorn

from fastapi import FastAPI

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from assets.python import slash_interactions as slash_interactions_handler

from cool_utils import Terminal
from discord_webhook import DiscordWebhook, DiscordEmbed

dir_path = os.path.dirname(os.path.realpath(__file__))

# nest_asyncio.apply()
internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
Client = internal.Client(constants)

SERVER_PORT = {
	"DEVELOPMENT": 2010,
	"PRODUCTION": 2000 
}

app = FastAPI(
	docs_url = None,
	redoc_url = None
)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request : Request):
	return "This is Senarc Core API."

app.include_router(slash_interactions_handler.Router)

if __name__ == '__main__':
	try:
		uvicorn.run(
			"main:app",
			host = '127.0.0.1',
			port = SERVER_PORT[internal.Constants.fetch("ENVIRONMENT")],
			reload = True,
			debug = True,
			workers = 2
		)
		Terminal.display("Server has Started")
	except Exception as error:
		webhook_url = Internal.Constants.fetch("WEBHOOKS")['errors']
		webhook = DiscordWebhook(url=webhook_url)
		embed = DiscordEmbed(description=f"```py\n{error}\n{error.__traceback__}\n```", color=0x90B5F8)
		embed.set_footer(text="Senarc API for developers")
		webhook.add_embed(embed)
		webhook.execute()

import os

from assets.python.internal import Internal

import uvicorn
import datetime

from fastapi import FastAPI

from fastapi import Request
from fastapi.responses import HTMLResponse

from assets.python import slash_interactions as slash_interactions_handler

from cool_utils import Terminal

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
	# Write current time in json to file
	with open("./assets/json/uptime.json", "rw") as file:
		file.write(int(datetime.datetime.now().timestamp()))

	uvicorn.run(
		"main:app",
		host = '127.0.0.1',
		port = SERVER_PORT[internal.Constants.fetch("ENVIRONMENT")],
		reload = True,
		debug = True,
		workers = 2
	)
	Terminal.display("Server has Started")

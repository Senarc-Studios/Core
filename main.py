import os

from assets.python.internal import Internal

import json
import uvicorn
import datetime

from fastapi import FastAPI

from fastapi import Request
from fastapi.responses import HTMLResponse

from assets.python import github as github_handler
from assets.python import uptime as uptime_handler
from assets.python import slash_interactions as slash_interactions_handler

from cool_utils import Terminal

dir_path = os.path.dirname(os.path.realpath(__file__))

internal = Internal()
constants = internal.Constants("./assets/json/constants.json")
Client = internal.Client(constants)

SERVER_PORT = {
	"DEVELOPMENT": 8080,
	"PRODUCTION": 8000
}

app = FastAPI(
	docs_url = None,
	redoc_url = None
)

@app.get(
	"/",
	response_class = HTMLResponse,
	include_in_schema = False
)
async def home(request: Request):
	return "This is Senarc Core API."

app.include_router(github_handler.Router)
app.include_router(uptime_handler.Router)
app.include_router(slash_interactions_handler.Router)

if __name__ == '__main__':
	uvicorn.run(
		"main:app",
		host = '127.0.0.1',
		port = SERVER_PORT[internal.Constants.fetch("ENVIRONMENT")],
		reload = True,
		debug = True,
		workers = 2
	)
	Terminal.display("Server has Started")

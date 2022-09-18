import json
import datetime

from fastapi import APIRouter
from fastapi import Request

Router = APIRouter(
    prefix = "/uptime",
)

@Router.get("/")
async def uptime(request: Request):
    # Load uptime.json
    with open("./assets/json/uptime.json", "r") as file:
        data = json.loads(file.read())
    
    # Calculate the uptime
    uptime = int(datetime.datetime.now().timestamp()) - int(data)
    
    # Return the uptime
    return {
        "uptime": uptime
    }, 200
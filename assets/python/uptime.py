import os
import json
import datetime

from fastapi import APIRouter
from fastapi import Request

Router = APIRouter()

@Router.get("/uptime")
async def uptime(request: Request):
    return "Core API is Online."
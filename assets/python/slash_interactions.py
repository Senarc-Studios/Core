from fastapi import APIRouter
# Import global_func from 3 directories up
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

Router = APIRouter(
	prefix="/discord"
)
ENDPOINT_URL = f"https://discord.com/api/v10/applications/{Router.Internal.Client.id}/guilds/{Router.Internal.Client.core_guild_id}/commands"
DISCORD_HEADERS = {
	"Authorization": f"Bot {Router.Internal.Client.token}"
}

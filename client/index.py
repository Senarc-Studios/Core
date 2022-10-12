from assets.python.internal import Internal

from cool_utils import Terminal

from discord import Embed, Intents
from discord.ext.commands import Bot

Internal = Internal()
Constants = Internal.Constants("./assets/json/constants.json")
fetch_list = (
	"CLIENT_TOKEN",
	"CHANNELS",
	"MONGO",
	"ROLES",
	"ENVIRONMENT"
)
intents = Intents.all()
bot = Bot(
	command_prefix = "sca!",
	intents = intents
)

for constant in fetch_list:
	Constants.fetch(constant)

@bot.listen("on_ready")
async def startup():
	Terminal.display("Bot is ready.")

@bot.listen("on_member_join")
async def greet_new_members(member):
	Terminal.display(f"{member.name} has joined the guild.")
	embed = Embed(
		timestamp = member.joined_at,
		description = f"Welcome to **Senarc**'s Core Guild, we hope you have a nice stay!",
		colour = 0x35393f
	)
	embed.set_author(
		name = f"{member.name} Joined!",
		icon_url = member.avatar_url
	)
	embed.set_footer(
		text = f"Senarc Core",
		icon_url = bot.user.avatar_url
	)
	role = await member.guild.fetch_role(Constants.get("ROLES").get("MEMBER"))
	await member.add_roles(role)
	except Exception as error:
		print(error)
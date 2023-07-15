from assets.python.internal import Internal

from discord import Embed
from discord.ext.commands import Cog

from profanityfilter import ProfanityFilter

internal = Internal()
Constants = internal.Constants("./assets/json/constants.json")
FETCH_LIST = (
	"CHANNELS",
)
for constant in FETCH_LIST:
	Constants.fetch(constant)

class Profanity(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.filter = ProfanityFilter()

    @Cog.listener("on_message")
    async def profanity_check(self, message):
        is_profane: bool = self.filter.is_profane(message.content)
        if is_profane:
            log_message = Embed(
                description = f"**Original Message:**\n{message.content}\n\n**Censored Message:**\n{self.filter.censor(message.content)}",
                colour = 0x2B2D31
            )
            log_message.set_author(
                name = message.author.global_name,
                icon_url = message.author.display_avatar.url
            )
            log_message.set_footer(
                text = "Senarc Core",
                icon_url = self.bot.user.display_avatar.url
            )

            log_channel = self.bot.get_channel(int(Constants.get("CHANNELS").get("AUTOMOD_LOGS")))
            await log_channel.send(embed = log_message)

            await message.delete()

async def setup(bot):
    await bot.add_cog(Profanity(bot))
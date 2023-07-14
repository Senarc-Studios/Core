from ..assets.python.internal import Internal

from discord import Embed
from discord.ext.commands import Cog

from profanity_check import predict_prob

internal = Internal()
Constants = internal.Constants
FETCH_LIST = (
	"CHANNELS"
)
for constant in FETCH_LIST:
	Constants.fetch(constant)

class Profanity(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener("on_message")
    async def profanity_check(self, message):
        probability: int = int(predict_prob([message.content])[0] * 100)
        if probability > 65:
            log_message = Embed(
                description = f"**Original Message:**\n{message.content}\n\n**Probability:**\n`{probability}%`",
                colour = 0x2B2D31
            )
            log_message.set_author(
                name = message.author.global_name,
                icon_url = message.author.display_avatar.url
            )
            log_message.set_footer(
                text = "Senarc Core",
                icon_url = self.bot.me.display_avatar.url
            )

            await message.delete()

            log_channel = self.bot.get_channel(Constants.get("CHANNELS").get("AUTOMOD_LOGS"))
            await log_channel.send(embed = log_message)

async def setup(bot):
    await bot.add_cog(Profanity(bot))
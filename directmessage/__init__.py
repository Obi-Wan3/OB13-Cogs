from .directmessage import DirectMessage


async def setup(bot):
    bot.add_cog(DirectMessage(bot))
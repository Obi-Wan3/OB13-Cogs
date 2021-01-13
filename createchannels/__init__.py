from .createchannels import CreateChannels


async def setup(bot):
    bot.add_cog(CreateChannels(bot))
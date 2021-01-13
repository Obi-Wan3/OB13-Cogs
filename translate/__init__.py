from .translate import Translate


async def setup(bot):
    bot.add_cog(Translate(bot))
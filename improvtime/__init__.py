from .improvtime import ImprovTime


async def setup(bot):
    bot.add_cog(ImprovTime(bot))
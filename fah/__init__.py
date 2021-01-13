from .fah import FaH


async def setup(bot):
    bot.add_cog(FaH(bot))

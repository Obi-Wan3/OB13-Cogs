from .counting import Counting


async def setup(bot):
    bot.add_cog(Counting(bot))
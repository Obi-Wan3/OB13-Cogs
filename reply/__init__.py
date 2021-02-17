from .reply import Reply


async def setup(bot):
    bot.add_cog(Reply(bot))
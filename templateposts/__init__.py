from .templateposts import TemplatePosts


async def setup(bot):
    bot.add_cog(TemplatePosts(bot))
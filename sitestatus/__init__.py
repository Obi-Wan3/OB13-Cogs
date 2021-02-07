from .sitestatus import SiteStatus


async def setup(bot):
    bot.add_cog(SiteStatus(bot))
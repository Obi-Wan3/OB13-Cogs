from .announcements import Announcements


async def setup(bot):
    bot.add_cog(Announcements(bot))
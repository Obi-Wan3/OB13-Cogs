from .publicrooms import PublicRooms


async def setup(bot):
    bot.add_cog(PublicRooms(bot))
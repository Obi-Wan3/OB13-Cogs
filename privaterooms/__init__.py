from .privaterooms import PrivateRooms


async def setup(bot):
    bot.add_cog(PrivateRooms(bot))
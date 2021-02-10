from .statusrole import StatusRole


async def setup(bot):
    bot.add_cog(StatusRole(bot))
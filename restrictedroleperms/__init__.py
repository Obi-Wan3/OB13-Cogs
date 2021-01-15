from .restrictedroleperms import RestrictedRolePerms


async def setup(bot):
    bot.add_cog(RestrictedRolePerms(bot))

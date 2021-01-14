from .referrals import Referrals


async def setup(bot):
    bot.add_cog(Referrals(bot))
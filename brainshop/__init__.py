from .brainshop import BrainShop


async def setup(bot):
    bot.add_cog(BrainShop(bot))
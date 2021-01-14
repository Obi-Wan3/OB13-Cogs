from .embedreact import EmbedReact


async def setup(bot):
    bot.add_cog(EmbedReact(bot))
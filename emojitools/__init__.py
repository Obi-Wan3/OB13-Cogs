from .EmojiTools import EmojiTools


async def setup(bot):
    bot.add_cog(EmojiTools(bot))
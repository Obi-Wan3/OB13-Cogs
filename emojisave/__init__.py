from .emojisave import EmojiSave


async def setup(bot):
    bot.add_cog(EmojiSave(bot))
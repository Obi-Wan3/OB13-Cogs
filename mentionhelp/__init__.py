from .mentionhelp import MentionHelp


async def setup(bot):
    bot.add_cog(MentionHelp(bot))
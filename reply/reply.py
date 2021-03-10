from redbot.core import commands
import discord
import typing


class Reply(commands.Cog):
    """Bot Replies to Messages"""

    def __init__(self, bot):
        self.bot = bot

    @commands.admin()
    @commands.command(name="reply")
    async def _reply(self, ctx: commands.Context, to_mention: typing.Optional[bool], message: discord.Message, *, content: str):
        """Reply to a message using the Discord reply feature."""
        if not to_mention:
            mention_author = False
        else:
            mention_author = to_mention

        try:
            await message.reply(content, mention_author=mention_author)
        except discord.Forbidden:
            return await ctx.send("I cannot reply to the message!")
        return await ctx.tick()

from redbot.core import commands
import discord


class DirectMessage(commands.Cog):
    """Send DMs as the bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="directmessage", aliases=["sdm"])
    async def _direct_message(self, ctx: commands.Context, user: discord.User, *, message):
        """Sends a DM to a user (sends raw text directly)."""
        try:
            if user.dm_channel is None:
                await user.create_dm()
            await user.dm_channel.send(message)
        except discord.Forbidden:
            await ctx.author.send(f"User does not have DMs enabled.")

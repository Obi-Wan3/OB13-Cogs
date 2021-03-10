from redbot.core import commands
import discord


class Announcements(commands.Cog):
    """
    Send Message w/ Role Ping.

    Server announcements in a particular channel w/ role ping.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.admin()
    @commands.command(name="announcement")
    async def _announcement(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role, *, message=""):
        """Send an announcement message to a specific channel with a role ping."""
        try:
            await ctx.guild.get_channel(channel.id).send(f"{role.mention} {message}", allowed_mentions=discord.AllowedMentions(roles=True))
            return await ctx.tick()
        except discord.Forbidden:
            return await ctx.send("I do not have permissions to send that message!")

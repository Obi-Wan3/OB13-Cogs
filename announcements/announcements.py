from redbot.core import commands
import discord


class Announcements(commands.Cog):
    """Server announcements."""

    def __init__(self, bot):
        self.bot = bot

    @commands.admin()
    @commands.command()
    async def announcement(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role, *, message=""):
        """Send an announcement message to a specific channel with a role ping."""
        guild = ctx.guild
        announcement = f"{role.mention} {message}"
        m = discord.AllowedMentions(roles=True)
        await guild.get_channel(channel.id).send(announcement, allowed_mentions=m)
        return await ctx.tick()

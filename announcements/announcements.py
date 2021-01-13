from redbot.core import commands
import discord


class Announcements(commands.Cog):
    """Server announcements."""

    def __init__(self, bot):
        self.bot = bot

    @commands.admin()
    @commands.command()
    async def announcement(self, ctx: commands.Context, channel: discord.TextChannel, role: int, *, message=""):
        """Send an announcement message to a specific channel with a role ping."""
        guild = ctx.guild
        r = discord.utils.get(guild.roles, id=role)
        if r is None:
            await ctx.tick()
            return await ctx.send("Invalid role entered.")

        announcement = f"{r.mention} {message}"
        m = discord.AllowedMentions(roles=True)
        await guild.get_channel(channel.id).send(announcement, allowed_mentions=m)
        return await ctx.tick()
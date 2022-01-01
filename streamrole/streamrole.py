"""
MIT License

Copyright (c) 2021-present Obi-Wan3

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import typing

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list


class StreamRole(commands.Cog):
    """
    Roles for Discord Streamers

    Automatically give roles to users going live in Discord.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": False,
            "log": None,
            "stream_roles": {}
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_voice_state_update")
    async def _voice_listener(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if (
            not await self.config.guild(member.guild).toggle() or  # StreamRole toggled off
            member.bot or  # Member is a bot
            await self.bot.cog_disabled_in_guild(self, member.guild) or  # Cog disabled in guild
            not member.guild.me.guild_permissions.manage_roles  # Cannot manage roles
        ):
            return

        settings: dict = await self.config.guild(member.guild).stream_roles()
        log_channel = await self.config.guild(member.guild).log()
        if log_channel:
            log_channel = member.guild.get_channel(log_channel)
            perms = log_channel.permissions_for(member.guild.me)
            if not perms.send_messages:
                log_channel = None

        # User started streaming
        if not (before.channel and before.self_stream) and after.self_stream:
            for role, channels in settings.items():
                if after.channel.id in channels or (after.channel.category_id and after.channel.category_id in channels):
                    r = member.guild.get_role(int(role))
                    if r in member.roles or r >= member.guild.me.top_role:
                        continue

                    await member.add_roles(r, reason=f"StreamRole: {member.display_name} started streaming in {after.channel.name}")
                    if log_channel:
                        await log_channel.send(
                            f"{member.mention} was given {r.mention} as they started streaming in {after.channel.name}.",
                            allowed_mentions=discord.AllowedMentions.none()
                        )

        # User stopped streaming
        if before.self_stream and not (after.channel and after.self_stream):
            for role, channels in settings.items():
                if before.channel.id in channels or (before.channel.category_id and before.channel.category_id in channels):
                    r = member.guild.get_role(int(role))
                    if r not in member.roles or r >= member.guild.me.top_role:
                        continue

                    await member.remove_roles(r, reason=f"StreamRole: {member.display_name} stopped streaming in {before.channel.name}")
                    if log_channel:
                        await log_channel.send(
                            f"{r.mention} was removed from {member.mention} as they stopped streaming in {before.channel.name}.",
                            allowed_mentions=discord.AllowedMentions.none()
                        )

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="streamrole")
    async def _stream_role(self, ctx: commands.Context):
        """StreamRole Settings"""

    @_stream_role.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle StreamRole server-wide."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_stream_role.command(name="logchannel")
    async def _log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the StreamRole log channel (leave blank to remove)."""
        await self.config.guild(ctx.guild).log.set(channel.id if channel else None)
        return await ctx.tick()

    @_stream_role.command(name="add")
    async def _add(self, ctx: commands.Context, role: discord.Role, *channels: typing.Union[discord.VoiceChannel, discord.CategoryChannel]):
        """Add a new StreamRole to VCs and/or Categories."""
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("That role is above you in the role hierarchy!")

        async with self.config.guild(ctx.guild).stream_roles() as settings:
            if existing := settings.get(str(role.id)):
                for c in channels:
                    if c.id not in existing:
                        settings[str(role.id)].append(c.id)
            else:
                settings[str(role.id)] = [c.id for c in channels]

        return await ctx.tick()

    @_stream_role.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, role: discord.Role, *channels: typing.Union[discord.VoiceChannel, discord.CategoryChannel]):
        """Remove a StreamRole from VCs and/or Categories."""

        async with self.config.guild(ctx.guild).stream_roles() as settings:
            if existing := settings.get(str(role.id)):
                for c in channels:
                    if c.id in existing:
                        settings[str(role.id)].remove(c.id)
                if not settings[str(role.id)]:
                    del settings[str(role.id)]
            else:
                return await ctx.send("There are no VCs or Categories with that StreamRole!")

        return await ctx.tick()

    @_stream_role.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the server settings for StreamRole."""
        settings = await self.config.guild(ctx.guild).all()

        logchannel = None
        if settings['log'] and (lc := ctx.guild.get_channel(int(settings['log']))):
            logchannel = lc.mention

        embed = discord.Embed(
            title="StreamRole Settings",
            color=await ctx.embed_color(),
            description=f"**Toggle:** {settings['toggle']}\n**Log Channel:** {logchannel}"
        )

        roles = ""
        for r, c_list in settings['stream_roles'].items():
            if ro := ctx.guild.get_role(int(r)):
                channels = [ctx.guild.get_channel(int(c)).name if ctx.guild.get_channel(int(c)) else "" for c in c_list]
                roles += f"**{ro.mention}**: {humanize_list(list(filter(bool, channels)))}\n"

        embed.add_field(name="StreamRoles", value=roles or "None")

        return await ctx.send(embed=embed)

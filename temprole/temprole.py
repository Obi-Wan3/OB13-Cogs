"""
MIT License

Copyright (c) 2021 Obi-Wan3

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
import asyncio
from datetime import datetime, timedelta

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list

if typing.TYPE_CHECKING:
    TimeConverter = timedelta
else:
    TimeConverter = commands.converter.TimedeltaConverter(
        minimum=timedelta(hours=1),
        allowed_units=["weeks", "days", "hours"],
        default_unit="days"
    )


class TempRole(commands.Cog):
    """
    Assign Temporary Roles

    Give temporary roles to users, expiring after a set time.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "log": None
        }
        default_member = {
            "temp_roles": {}
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.tr_handler_task = self.bot.loop.create_task(self._tr_handler())

    def cog_unload(self):
        self.tr_handler_task.cancel()

    @commands.guild_only()
    @commands.group(name="temprole")
    async def _temp_role(self, ctx: commands.Context):
        """TempRole Commands"""

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @_temp_role.command(name="add")
    async def _add(self, ctx: commands.Context, user: discord.Member, role: discord.Role, *, time: TimeConverter):
        """
        Assign a temporary role to expire after a time.

        For the time, enter in terms of weeks (w), days (d), and/or hours (h).
        """
        if role in user.roles:
            return await ctx.send(f"That user already has {role.mention}!")

        if role >= ctx.guild.me.top_role or (role >= ctx.author.top_role and ctx.author != ctx.guild.owner):
            return await ctx.send("That role cannot be assigned due to the Discord role hierarchy!")

        async with self.config.member(user).temp_roles() as user_tr:
            if user_tr.get(str(role.id)):
                return await ctx.send(
                    f"That is already an active TempRole for {user.mention}!",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            end_time = datetime.now() + time
            user_tr[str(role.id)] = end_time.timestamp()

        try:
            await user.add_roles(
                role,
                reason=f"TempRole: added by {ctx.author}, expires in {time.days}d {time.seconds//3600}h"
            )

            message = f"TempRole {role.mention} for {user.mention} has been added. Expires in {time.days} days {time.seconds//3600} hours."
            await ctx.send(
                message,
                allowed_mentions=discord.AllowedMentions.none()
            )

            await self._maybe_send_log(ctx.guild, message)
            await self._tr_timer(user, role, end_time.timestamp())
        except (discord.Forbidden, discord.HTTPException):
            return await ctx.send("Something went wrong while assigning this role.")

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @_temp_role.command(name="remove")
    async def _remove(self, ctx: commands.Context, user: discord.Member, role: discord.Role):
        """Cancel the timer & remove a TempRole from a user."""
        async with self.config.member(user).temp_roles() as user_tr:
            if not (user_tr.get(str(role.id))):
                return await ctx.send(
                    f"That is not an active TempRole for {user.mention}.",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            del user_tr[str(role.id)]
        message = f"TempRole {role.mention} for {user.mention} has been removed."
        await ctx.send(
            message,
            allowed_mentions=discord.AllowedMentions.none()
        )
        await self._maybe_send_log(ctx.guild, message)
        await self._tr_end(user, role, admin=ctx.author)

    @_temp_role.command(name="remaining")
    async def _remaining(self, ctx: commands.Context, role: discord.Role):
        """See the time remaining for your TempRole."""
        user = ctx.author
        async with self.config.member(user).temp_roles() as user_tr:
            if not (cur_tr := user_tr.get(str(role.id))):
                return await ctx.send(
                    f"That is not an active TempRole for {user.mention}.",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            r_time = datetime.fromtimestamp(cur_tr) - datetime.now()
            return await ctx.maybe_send_embed(f"**Time remaining:** {r_time.days} days {round(r_time.seconds/3600, 1)} hours")

    @commands.bot_has_permissions(embed_links=True)
    @commands.admin_or_permissions(manage_roles=True)
    @_temp_role.command(name="list")
    async def _list(self, ctx: commands.Context, user: discord.Member = None):
        """List the active TempRoles for each user (or users with TempRoles in the server if user param is empty)."""
        desc = ""
        if not user:
            title = f"{ctx.guild.name} TempRoles"
            for member_id, temp_roles in (await self.config.all_members(ctx.guild)).items():
                member: discord.Member = ctx.guild.get_member(int(member_id))
                if member:
                    roles = [ctx.guild.get_role(int(r)) for r in temp_roles["temp_roles"].keys()]
                    desc += f"{member.mention}: {humanize_list([r.mention for r in roles])}\n"
        else:
            title = f"{user.display_name} TempRoles"
            async with self.config.member(user).temp_roles() as member_temp_roles:
                for temp_role, end_ts in member_temp_roles.items():
                    role: discord.Role = ctx.guild.get_role(int(temp_role))
                    if role:
                        r_time = datetime.fromtimestamp(end_ts) - datetime.now()
                        desc += f"{role.mention}: ends in {r_time.days}d {round(r_time.seconds/3600, 1)}h\n"
                    else:
                        del member_temp_roles[temp_role]
        return await ctx.send(embed=discord.Embed(
            title=title,
            description=desc,
            color=await ctx.embed_color()
        ))

    @commands.admin_or_permissions(manage_roles=True)
    @_temp_role.command(name="logchannel")
    async def _log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the TempRole log channel for the server (leave blank to remove)."""
        if channel and not channel.permissions_for(ctx.guild.me).send_message:
            return await ctx.send(f"I cannot send messages to {channel.mention}!")
        await self.config.guild(ctx.guild).log.set(channel.id if channel else None)
        return await ctx.tick()

    async def _maybe_send_log(self, guild: discord.Guild, message: str):
        log_channel = await self.config.guild(guild).log()
        if log_channel:
            try:
                await guild.get_channel(log_channel).send(
                    message,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except discord.HTTPException:
                pass

    async def _tr_handler(self):
        await self.bot.wait_until_red_ready()
        try:
            tr_coros = []
            for guild_id, members in (await self.config.all_members()).items():
                guild: discord.Guild = self.bot.get_guild(int(guild_id))
                for member_id, temp_roles in members.items():
                    member: discord.Member = guild.get_member(int(member_id))
                    for tr, ts in temp_roles["temp_roles"].items():
                        role: discord.Role = guild.get_role(int(tr))
                        tr_coros.append(self._tr_timer(member, role, ts))
            await asyncio.gather(*tr_coros)
        except Exception:
            pass

    async def _tr_timer(self, member: discord.Member, role: discord.Role, end_timestamp: float):
        seconds_left = (datetime.fromtimestamp(end_timestamp) - datetime.now()).total_seconds()
        if seconds_left > 0:
            await asyncio.sleep(seconds_left)
        await self._tr_end(member, role)

    async def _tr_end(self, member: discord.Member, role: discord.Role, admin=None):
        async with self.config.member(member).temp_roles() as tr_entries:
            if tr_entries.get(str(role.id)):
                del tr_entries[str(role.id)]
                reason = "TempRole: timer ended" if not admin else f"TempRole: timer ended early by {admin}"
                try:
                    await member.remove_roles(role, reason=reason)
                    await self._maybe_send_log(
                        member.guild,
                        f"TempRole {role.mention} for {member.mention} has been removed."
                    )
                except discord.Forbidden:
                    await self._maybe_send_log(
                        member.guild,
                        f"TempRole {role.mention} for {member.mention} was unable to be removed due to a lack of permissions."
                    )
                except discord.HTTPException:
                    await self._maybe_send_log(
                        member.guild,
                        f"TempRole {role.mention} for {member.mention} was unable to be removed due an error."
                    )

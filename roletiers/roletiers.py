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

from datetime import datetime, timedelta

import discord
from discord.ext import tasks
from .configcache import GuildCache, MemberCache
from redbot.core import commands, Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, humanize_timedelta


DEFAULT_INTERVAL = 15


class RoleTiers(commands.Cog):
    """
    Tiered Roles for Active Members

    Set roles to be assigned based on the activity and time since join for members.
    """

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)

        default_global = {
            "interval": DEFAULT_INTERVAL
        }
        self.default_guild = {
            "toggle": False,
            "count_commands": False,
            "tiers": [],
            "ignore": []
        }
        self.default_member = {
            "messages": 0
        }

        self.config.register_global(**default_global)
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)

        self.guild_settings: GuildCache = GuildCache()
        self.member_data: MemberCache = MemberCache()

    async def initialize(self):

        # Cache config
        self.guild_settings.initialize(await self.config.all_guilds(), self.default_guild)
        self.member_data.initialize(await self.config.all_members(), self.default_member)

        # Start loops
        self._config_cache.start()
        self._tier_checker.start()

        # Change loop interval if necessary
        if (interval := await self.config.interval()) != DEFAULT_INTERVAL:
            self._tier_checker.change_interval(minutes=interval)

    def cog_unload(self):
        self._config_cache.cancel()
        self._tier_checker.cancel()

    @staticmethod
    async def _seconds_since(time: datetime):
        return (datetime.utcnow() - time).total_seconds()

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):

        # Ignore these messages
        if (
                not message.guild or  # Message not in a guild
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not self.guild_settings.get(message.guild.id, "toggle") or  # RoleTiers toggled off
                message.author.bot or  # Message author is a bot
                message.author.id in self.guild_settings.get(message.guild.id, "ignore")  # Message from ignored user
        ):
            return

        self.member_data.increment(message.guild.id, message.author.id, "messages", 1)

    @commands.Cog.listener("on_command")
    async def _command_listener(self, message: discord.Message):
        if message.guild and self.guild_settings.get(message.guild.id, "count_commands"):
            await self._message_listener(message)

    @commands.Cog.listener("on_member_remove")
    async def _member_leave_listener(self, member: discord.Member):

        # Ignore these messages
        if (
                await self.bot.cog_disabled_in_guild(self, member.guild) or  # Cog disabled in guild
                not self.guild_settings.get(member.guild.id, "toggle") or  # RoleTiers toggled off
                member.bot or  # Member is a bot
                member.id in self.guild_settings.get(member.guild.id, "ignore")  # Member is ignored user
        ):
            return

        self.member_data.set(member.guild.id, member.id, "messages", 0)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="roletiers")
    async def _role_tiers(self, ctx: commands.Context):
        """
        RoleTiers Settings

        Create tiers with set roles to be assigned based on the activity and time since join for members. Users will be given the role associated with the highest tier they are eligible for, based on the defined threshold of a tier. A user does not have to qualify for a lower tier to be given a higher tier, and users manually assigned any role are assumed to be in the highest tier assigning that role.
        """

    @commands.is_owner()
    @commands.command(name="interval", hidden=True)
    async def _interval(self, ctx: commands.Context, interval_in_minutes: int):
        """
        Set the global tier-checking interval for RoleTiers.

        Depending on the size of your bot, you may want to modify the interval for which the bot checks tiers for members in all guilds (default is 15 minutes).
        """
        await self.config.interval.set(interval_in_minutes)
        self._tier_checker.change_interval(minutes=interval_in_minutes)
        return await ctx.send(f"I will now check tiers for all members every {interval_in_minutes} minutes (change takes effect next loop).")

    @_role_tiers.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle RoleTiers in this server."""
        self.guild_settings.set(ctx.guild.id, "toggle", true_or_false)
        return await ctx.tick()

    @_role_tiers.command(name="countcommands")
    async def _count_commands(self, ctx: commands.Context, true_or_false: bool):
        """Set whether RoleTiers should count commands when counting messages."""
        self.guild_settings.set(ctx.guild.id, "count_commands", true_or_false)
        return await ctx.tick()

    @_role_tiers.group(name="ignore", invoke_without_command=True)
    async def _ignore(self, ctx: commands.Context):
        """View and set the RoleTiers user ignore list."""
        await ctx.maybe_send_embed(f"{humanize_list([f'{us.mention}' if (us := ctx.guild.get_member(u)) else f'{u}' for u in self.guild_settings.get(ctx.guild.id, 'ignore')])}" or "No users are on the RoleTiers ignore list yet.")
        await ctx.send_help()

    @_ignore.command("add", require_var_positional=True)
    async def _ignore_add(self, ctx: commands.Context, *users: discord.Member):
        """Add to the RoleTiers ignored users list."""
        for u in users:
            self.guild_settings.append(ctx.guild.id, "ignore", u.id, check=True)
        return await ctx.tick()

    @_ignore.command("remove", aliases=["delete"], require_var_positional=True)
    async def _ignore_remove(self, ctx: commands.Context, *users: discord.Member):
        """Remove from the RoleTiers ignored users list."""
        for u in users:
            self.guild_settings.remove(ctx.guild.id, "ignore", u.id, check=True)
        return await ctx.tick()

    @_role_tiers.command(name="addtier", aliases=["add"])
    async def _add_tier(self, ctx: commands.Context, tier: int, role: discord.Role, messages: int, hours: int, remove: bool):
        """
        Add a tier to the server RoleTiers (parameters below).

        `tier`: the position in the tier hierarchy (`1` for the lowest tier)
        `role`: the role to be assigned
        `messages`: the # of required messages users must have sent
        `hours`: the time (in hours) users must have been in the server for
        `remove`: whether to remove the roles assigned by previous tiers
        """

        if messages < 0:
            return await ctx.send("Please enter a non-negative integer for `messages`!")

        if hours < 0:
            return await ctx.send("Please enter a non-negative integer for `hours`!")

        # Role hierarchy check
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("The role you provided is above you in the role hierarchy!")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("The role you provided is above me in the role hierarchy!")

        async with self.config.guild(ctx.guild).tiers() as guild_tiers:

            for guild_tier in guild_tiers:
                if guild_tier["role"] == role.id and guild_tier["messages"] == messages and guild_tier["hours"] == hours:
                    return await ctx.send("There is already an identical tier!")

            guild_tiers.insert(
                tier-1,
                {
                    "role": role.id,
                    "messages": messages,
                    "hours": hours,
                    "remove": remove
                }
            )

        return await ctx.send("Tier successfully added.")

    @_role_tiers.group(name="edittier", aliases=["edit"])
    async def _edit_tier(self, ctx: commands.Context):
        """Edit a RoleTier's requirements and details."""

    @_edit_tier.command(name="position")
    async def _edit_position(self, ctx: commands.Context, tier: int, new_position: int):
        """Edit a RoleTier's position in the tier hierarchy."""
        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            try:
                guild_tiers.insert(new_position-1, guild_tiers.pop(tier-1))
            except IndexError:
                return await ctx.send(f"Tier {tier} was not found.")
        return await ctx.tick()

    @_edit_tier.command(name="role")
    async def _edit_role(self, ctx: commands.Context, tier: int, role: discord.Role):
        """Edit a RoleTier's role to be assigned."""
        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            try:
                guild_tiers[tier-1]["role"] = role.id
            except IndexError:
                return await ctx.send(f"Tier {tier} was not found.")
        return await ctx.tick()

    @_edit_tier.command(name="messages")
    async def _edit_messages(self, ctx: commands.Context, tier: int, messages: int):
        """Edit a RoleTier's message count requirement."""
        if messages < 0:
            return await ctx.send("Please enter a non-negative integer for `messages`!")

        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            try:
                guild_tiers[tier - 1]["messages"] = messages
            except IndexError:
                return await ctx.send(f"Tier {tier} was not found.")
        return await ctx.tick()

    @_edit_tier.command(name="hours")
    async def _edit_hours(self, ctx: commands.Context, tier: int, hours: int):
        """Edit a RoleTier's hours-since-join requirement."""
        if hours < 0:
            return await ctx.send("Please enter a non-negative integer for `hours`!")

        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            try:
                guild_tiers[tier - 1]["hours"] = hours
            except IndexError:
                return await ctx.send(f"Tier {tier} was not found.")
        return await ctx.tick()

    @_edit_tier.command(name="remove")
    async def _edit_remove(self, ctx: commands.Context, tier: int, remove: bool):
        """Edit whether a RoleTier should remove roles assigned by previous tiers."""
        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            try:
                guild_tiers[tier - 1]["remove"] = remove
            except IndexError:
                return await ctx.send(f"Tier {tier} was not found.")
        return await ctx.tick()

    @_role_tiers.command(name="removetier", aliases=["remove", "delete"])
    async def _remove_tier(self, ctx: commands.Context, tier: int):
        """
        Remove a tier from the server RoleTiers.

        Enter the tier number/position to remove (see `[p]roletiers view`).
        """

        async with self.config.guild(ctx.guild).tiers() as guild_tiers:
            if not 0 <= tier-1 < len(guild_tiers):
                return await ctx.send(f"Tier {tier} does not exist!")
            guild_tiers.pop(tier-1)

        return await ctx.send("Tier removed successfully.")

    @_role_tiers.command(name="user")
    async def _user(self, ctx: commands.Context, user: discord.Member):
        """View a user's RoleTiers stats."""
        messages = self.member_data.get(ctx.guild.id, user.id, "messages")
        seconds = int(await self._seconds_since(user.joined_at))
        return await ctx.maybe_send_embed(f"**Messages Sent:** {messages}\n**Time Since Join:** {humanize_timedelta(timedelta=(timedelta(seconds=(seconds - seconds%3600)))) or '< 1 hour'}")

    @_role_tiers.command(name="forcecheck", hidden=True)
    async def _force_check(self, ctx: commands.Context, enter_true_to_confirm: bool):
        """Force a run of the tier-checking loop."""
        if not enter_true_to_confirm:
            return await ctx.send("Please enter `true` to confirm this action!")
        async with ctx.typing():
            await self._tier_checker.coro(self, guild_to_check=ctx.guild.id)
        return await ctx.tick()

    @_role_tiers.command(name="resetusers", hidden=True)
    async def _reset_users(self, ctx: commands.Context, enter_true_to_confirm: bool):
        """Reset all users' message counts for this server (warning: this cannot be undone)."""
        if not enter_true_to_confirm:
            return await ctx.send("Please enter `true` to confirm this action!")
        await self.config.clear_all_members(guild=ctx.guild)
        self.member_data.cache[ctx.guild.id] = {}
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_role_tiers.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the RoleTiers settings for this server."""

        guild_settings = self.guild_settings.get(ctx.guild.id)

        embed = discord.Embed(
            title="RoleTiers Settings",
            description=f"**Toggle:** {guild_settings['toggle']}\n**Count Commands:** {guild_settings['count_commands']}\n**Ignored Users:** see `{ctx.clean_prefix}roletiers ignore`",
            color=await ctx.embed_color()
        )

        guild_tiers = await self.config.guild(ctx.guild).tiers()

        invalid_tiers = []

        for i in range(len(guild_tiers)):
            if not (role := ctx.guild.get_role(guild_tiers[i]["role"])):
                invalid_tiers.append(i)
                continue

            tier_info = [
                f"**Role to Assign:** {role.mention}",
                f"**Messages Sent:** {guild_tiers[i]['messages']}",
                f"**Hours In Server:** {guild_tiers[i]['hours']}",
                f"**Remove Prev. Roles:** {guild_tiers[i]['remove']}"
            ]

            embed.add_field(
                name=f"Tier {i+1}",
                value="\n".join(tier_info),
                inline=False
            )

        if invalid_tiers:
            new_tiers = []
            for t in range(len(guild_tiers)):
                if t not in invalid_tiers:
                    new_tiers.append(guild_tiers[t])
            await self.config.guild(ctx.guild).tiers.set(new_tiers)

        return await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def _config_cache(self):

        # Cache guild settings
        async for guild_id, guild_settings in AsyncIter(self.guild_settings.items(), steps=500):
            async with self.config.guild_from_id(guild_id).all() as guild_config:
                guild_config["toggle"] = guild_settings["toggle"]
                guild_config["count_commands"] = guild_settings["count_commands"]
                guild_config["ignore"] = guild_settings["ignore"]

        # Cache member settings
        for guild_id, guild_members in self.member_data.items():
            async for member_id, member_settings in AsyncIter(guild_members.items(), steps=500):
                async with self.config.member_from_ids(guild_id, member_id).all() as member_config:
                    member_config["messages"] = member_settings["messages"]

    @_config_cache.before_loop
    async def _before_config_cache(self):
        await self.bot.wait_until_red_ready()

    @_config_cache.after_loop
    async def _after_config_cache(self):
        if self._config_cache.is_being_cancelled():
            await self._config_cache.coro(self)

    @tasks.loop(minutes=DEFAULT_INTERVAL)
    async def _tier_checker(self, guild_to_check=None):

        # Loop through each guild
        for guild_id, guild_settings in self.guild_settings.items():

            # Check for single guild
            if guild_to_check and guild_id != guild_to_check:
                continue

            # Checks for guild
            if (
                    not (guild := self.bot.get_guild(guild_id)) or  # No longer in guild
                    await self.bot.cog_disabled_in_guild(self, guild) or  # Cog disabled in guild
                    not self.guild_settings.get(guild_id, "toggle") or  # RoleTiers toggled off
                    not guild.me.guild_permissions.manage_roles  # Cannot manage roles
            ):
                continue

            # Validate tiers & fetch roles
            guild_tiers_config: list = await self.config.guild(guild).tiers()
            guild_tiers: list = []
            for i in range(len(guild_tiers_config)):
                if role := guild.get_role(guild_tiers_config[i]["role"]):
                    guild_tiers.append(guild_tiers_config[i])
                    guild_tiers[i].update(role=role)

            # Loop through each member
            async for member in AsyncIter(guild.members, steps=100):

                # Check ignore list
                if member.id in guild_settings["ignore"]:
                    continue

                member_settings = self.member_data.get(guild_id, member.id)

                member_roles = [r.id for r in member.roles]
                member_tier_roles, new_tier = [], None

                # Check each tier
                for tier in reversed(guild_tiers):

                    # Member currently in tier
                    if tier["role"].id in member_roles:
                        if tier["role"] not in member_tier_roles:
                            member_tier_roles.append(tier["role"])

                    # Check if member qualifies for tier
                    elif (
                            not new_tier and  # Does not already have a newly qualified higher tier
                            not member_tier_roles and  # Member is not already in a higher tier
                            ((await self._seconds_since(member.joined_at)) / 3600 >= tier["hours"]) and  # Time since join qualified
                            (member_settings["messages"] >= tier["messages"])  # Message requirement satisfied
                    ):
                        new_tier = tier

                # Add role from new tier
                if new_tier and new_tier["role"] and new_tier["role"] < guild.me.top_role:
                    await member.add_roles(new_tier["role"], reason="RoleTiers: member reached new tier")

                # Remove roles from prior tiers
                if new_tier and new_tier["remove"] and (member_tier_roles := [role for role in member_tier_roles if role < guild.me.top_role]):
                    await member.remove_roles(*member_tier_roles, reason="RoleTiers: removing roles from prior tiers")

    @_tier_checker.before_loop
    async def _before_checker(self):
        await self.bot.wait_until_red_ready()

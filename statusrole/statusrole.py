from redbot.core import commands, Config
import discord
import typing
import re


class StatusRole(commands.Cog):
    """
    Roles for Certain Custom Statuses

    Assign roles to users for the duration in which they have certain custom statuses.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "roles": {},
            "channel": None,
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_member_update")
    async def _member_update_listener(self, before: discord.Member, after: discord.Member):
        if (
            before.bot or  # Member is a bot
            await self.bot.cog_disabled_in_guild(self, before.guild)  # Cog disabled in guild
        ):
            return

        # Activity did not change
        if before.activity == after.activity:
            return

        log_channel = await self.config.guild(before.guild).channel()
        if log_channel:
            log_channel = before.guild.get_channel(log_channel)

        async with self.config.guild(before.guild).roles() as status_roles:
            for name, sr in status_roles.items():
                if not sr["toggle"]:
                    continue

                role = before.guild.get_role(sr["role"])
                before_status = await self._custom_activity(before.activities)
                after_status = await self._custom_activity(after.activities)

                # Now have custom status (did not have before)
                if not before_status and after_status:
                    if await self._status_matches(sr["status"], sr["emoji"], after_status):
                        try:
                            await after.add_roles(role, reason=f"StatusRole: new custom status matched {name}")
                            if log_channel:
                                await self._send_log(log_channel, True, after, role, after_status.name, after_status.emoji.name if after_status.emoji else "None")
                        except discord.Forbidden:
                            pass

                # Had custom status (does not anymore)
                elif before_status and not after_status:
                    if await self._status_matches(sr["status"], sr["emoji"], before_status):
                        try:
                            await after.remove_roles(role, reason=f"StatusRole: custom status no longer matches {name}")
                            if log_channel:
                                await self._send_log(log_channel, False, after, role, "None", "None")
                        except discord.Forbidden:
                            pass

                # Custom status changed
                elif before_status and after_status and before_status != after_status:
                    before_match = await self._status_matches(sr["status"], sr["emoji"], before_status)
                    after_match = await self._status_matches(sr["status"], sr["emoji"], after_status)

                    if (
                            not before_match and after_match and  # New status matches
                            sr["role"] not in [r.id for r in after.roles]  # Does not already have role
                    ):
                        try:
                            await after.add_roles(role, reason=f"StatusRole: new custom status matched {name}")
                            if log_channel:
                                await self._send_log(log_channel, True, after, role, after_status.name, after_status.emoji.name if after_status.emoji else "None")
                        except discord.Forbidden:
                            pass

                    elif (
                            before_match and not after_match and  # No longer matches
                            sr["role"] in [r.id for r in after.roles]  # Has role
                    ):
                        try:
                            await after.remove_roles(role, reason=f"StatusRole: custom status no longer matches {name}")
                            if log_channel:
                                await self._send_log(log_channel, False, after, role, after_status.name, after_status.emoji.name if after_status.emoji else "None")
                        except discord.Forbidden:
                            pass

    @staticmethod
    async def _custom_activity(activities):
        for act in activities:
            if isinstance(act, discord.CustomActivity):
                return act
        return None

    @staticmethod
    async def _status_matches(st, em, user_status):
        status = user_status.name
        emoji = user_status.emoji

        if (not st and not em) or (not status and not emoji):
            return False

        async def _st_match(r, s):
            if not r:  # No requirement
                return True
            else:
                if not s:
                    return False
                try:
                    return re.fullmatch(r, s)
                except re.error:
                    return False

        async def _em_match(r, e):
            if not r:  # No requirement
                return True
            else:
                if not e:
                    return False
                else:
                    if e.is_custom_emoji() and r[1] == e.id:  # Custom emoji matches
                        return True
                    elif e.is_unicode_emoji() and r[0] == e.name:  # Default emoji matches
                        return True

        return (await _st_match(st, status)) and (await _em_match(em, emoji))

    @staticmethod
    async def _send_log(channel: discord.TextChannel, assign: bool, user: discord.Member, role: discord.Role, status: str, emoji: str):
        embed = discord.Embed(title=f"StatusRole `{role.name}` ")
        embed.add_field(name="Member", value=user.mention)
        embed.add_field(name="New Status", value=f"`{status}`")
        embed.add_field(name="New Emoji", value=f"`{emoji}`")

        # Role assigned
        if assign:
            embed.title += "Added"
            embed.color = discord.Color.green()
            plaintext = f"StatusRole: {user.mention} custom status changed to `{status}` with emoji `{emoji}`, {role.mention} assigned"

        # Role removed
        else:
            embed.title += "Removed"
            embed.color = discord.Color.red()
            plaintext = f"StatusRole: {user.mention} custom status changed to `{status}` with emoji `{emoji}`, {role.mention} removed"

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            try:
                await channel.send(plaintext)
            except (discord.Forbidden, discord.HTTPException):
                pass
        except discord.HTTPException:
            pass

    @commands.guild_only()
    @commands.admin()
    @commands.group(name="statusrole")
    async def _status_role(self, ctx: commands.Context):
        """StatusRole Settings"""

    @_status_role.command(name="logchannel")
    async def _log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the StatusRole log channel (leave blank to disable logs)."""
        await self.config.guild(ctx.guild).channel.set(channel.id if channel else None)
        return await ctx.tick()

    @_status_role.command(name="add")
    async def _add(self, ctx: commands.Context, pair_name: str, role: discord.Role, *, custom_status_regex: str):
        """Add a role to be assigned to users with a matching emoji (optional) and custom status (accepts regex)."""
        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name in roles.keys():
                return await ctx.send("There is already a StatusRole with this name! Please edit/delete it or choose another name.")
            try:
                re.compile(custom_status_regex)
            except re.error:
                return await ctx.send("There was an error compiling that status regex. Is the regex valid?")
            roles[pair_name] = {
                "role": role.id,
                "emoji": None,
                "status": custom_status_regex,
                "toggle": True
            }
        return await ctx.send(f"`{role.name}` will now be assigned to users with any emoji and status matching the regex `{custom_status_regex}`.")

    @_status_role.group(name="edit")
    async def _edit(self, ctx: commands.Context):
        """Edit a StatusRole"""

    @_edit.command(name="role")
    async def _edit_role(self, ctx: commands.Context, pair_name: str, role: discord.Role):
        """Edit a StatusRole's role to be assigned."""
        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name not in roles.keys():
                return await ctx.send("There is no StatusRole with this name!")
            roles[pair_name]["role"] = role.id
        return await ctx.tick()

    @_edit.command(name="emoji")
    async def _edit_emoji(self, ctx: commands.Context, pair_name: str, emoji: typing.Union[discord.PartialEmoji, str] = None):
        """Edit a StatusRole's required emoji (leave blank to remove)."""
        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name not in roles.keys():
                return await ctx.send("There is no StatusRole with this name!")
            roles[pair_name]["emoji"] = ((emoji.name, emoji.id) if isinstance(emoji, discord.PartialEmoji) else (emoji, None)) if emoji else None
        return await ctx.tick()

    @_edit.command(name="status")
    async def _edit_status(self, ctx: commands.Context, pair_name: str, *, custom_status_regex: str = None):
        """Edit a StatusRole's custom status regex to be matched (leave blank to remove)."""
        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name not in roles.keys():
                return await ctx.send("There is no StatusRole with this name!")
            try:
                re.compile(custom_status_regex)
            except re.error:
                return await ctx.send("There was an error compiling that status regex. Is the regex valid?")
            roles[pair_name]["status"] = custom_status_regex
        return await ctx.tick()

    @_edit.command(name="toggle")
    async def _edit_toggle(self, ctx: commands.Context, pair_name: str, true_or_false: bool):
        """Toggle a StatusRole assignment temporarily."""
        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name not in roles.keys():
                return await ctx.send("There is no StatusRole with this name!")
            roles[pair_name]["toggle"] = true_or_false
        return await ctx.tick()

    @_status_role.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, pair_name: str, enter_true_to_confirm: bool):
        """Remove a StatusRole from being assigned."""
        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).roles() as roles:
            if pair_name not in roles.keys():
                return await ctx.send("There is no StatusRole with this name!")
            del roles[pair_name]
        return await ctx.tick()

    @_status_role.command(name="forcecheck")
    async def _force_update(self, ctx: commands.Context, *statusroles: str):
        """Force a manual check of every user on this server for the provided StatusRoles."""

        async with ctx.typing():
            log_channel = await self.config.guild(ctx.guild).channel()
            if log_channel:
                log_channel = ctx.guild.get_channel(log_channel)

            async with self.config.guild(ctx.guild).roles() as roles:
                for sr in statusroles:
                    if sr not in roles.keys():
                        await ctx.send(f"Skipping `{sr}` as there no StatusRole with that name.")
                        statusroles.remove(sr)

                members = ctx.guild.members
                await ctx.send(f"Updating `{len(statusroles)}` StatusRoles for all `{len(members)}` members in the server, this may take a while...")
                for m in members:
                    m_status = await self._custom_activity(m.activities)
                    if m_status:
                        for sr in statusroles:
                            if not roles[sr]["toggle"]:
                                await ctx.send(f"Skipping `{sr}` as it is toggled off.")
                                continue

                            r = ctx.guild.get_role(roles[sr]["role"]) if roles[sr]["role"] else None
                            if not r:
                                continue

                            if await self._status_matches(roles[sr]["status"], roles[sr]["emoji"], m_status):
                                if roles[sr]["role"] not in [r.id for r in m.roles]:  # Does not already have role
                                    await m.add_roles(r, reason=f"StatusRole ForceUpdate: custom status matched {sr}")
                                    if log_channel:
                                        await self._send_log(log_channel, True, m, r, m_status.name, m_status.emoji.name if m_status.emoji else "None")
                            else:
                                if roles[sr]["role"] in [r.id for r in m.roles]:  # Has role but status does not match
                                    await m.remove_roles(r, reason=f"StatusRole ForceUpdate: custom status does not match {sr}")
                                    if log_channel:
                                        await self._send_log(log_channel, False, m, r, m_status.name, m_status.emoji.name if m_status.emoji else "None")

        return await ctx.send("Force update completed!")

    @_status_role.command(name="view", aliases=["list"])
    async def _view(self, ctx: commands.Context):
        """View the StatusRole settings for this server."""
        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(
            title="StatusRole Settings",
            color=await ctx.embed_color(),
            description=f"Log Channel: {ctx.guild.get_channel(settings['channel']).mention if settings['channel'] else None}"
        )

        for name, statusrole in settings["roles"].items():
            embed.add_field(
                name=name,
                value=f"""
                **Role:** {ctx.guild.get_role(statusrole["role"]).mention}
                **Emoji:** {statusrole["emoji"][0] if statusrole["emoji"] else "Any"}
                **Status:** {statusrole["status"]}
                **Toggle:** {statusrole["toggle"]}
                """
            )

        return await ctx.send(embed=embed)

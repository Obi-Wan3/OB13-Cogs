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
import asyncio
from datetime import datetime, timedelta

import discord
from redbot.core import commands, Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, pagify

NOT_SUPPORTING = "You do not have BotAccess privileges!"
THANKS = "Thank you for supporting my server! Here is my invite link: <{invite}>. You can add a BotAccess server with `[p]botaccess servers add <server ID>`."
EXPIRE = "Unfortunately, your BotAccess servers have expired as you are no longer a supporter."


class BotAccess(commands.Cog):
    """
    Allow Special Roles Access to Bot

    Allow users with the Server Booster, Patreon, etc. roles to invite the bot to a (few) server(s) of their choice.
    """

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_global = {
            "allowed": [],
            "main_servers": {},
            "messages": {
                "thanks": {
                    "toggle": True,
                    "content": ""
                },
                "expire": {
                    "toggle": True,
                    "content": ""
                }
            },
            "not_supporting": "",
            "limit": 1,
            "auto_leave": {
                "toggle": True,
                "delay": 24
            },
        }
        default_user = {
            "servers": [],
            "supporting_in": [],
            "end_timestamp": None
        }
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)

        self.expire_handler_task = self.bot.loop.create_task(self._expire_handler())

    def cog_unload(self):
        self.expire_handler_task.cancel()

    @commands.Cog.listener("on_guild_join")
    async def _guild_join(self, guild: discord.Guild):
        # Check if bot owns guild
        if guild.owner and guild.owner == guild.me:
            return

        # Check if a bot owner owns guild
        if guild.owner_id in self.bot.owner_ids:
            return

        # Check if this is an allowed server
        if guild.id in await self.config.allowed():
            return

        # Check if this is a main server
        if str(guild.id) in (await self.config.main_servers()).keys():
            return

        # Check if this is a BotAccess server
        for data in (await self.config.all_users()).values():
            if guild.id in data["servers"]:
                return

        # Find inviter
        inviter = None
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                if entry.target == guild.me:
                    inviter = entry.user
                    break

        # DM inviter
        if inviter:
            try:
                await inviter.send(await self.config.not_supporting() or NOT_SUPPORTING)
            except discord.HTTPException:
                pass
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(await self.config.not_supporting() or NOT_SUPPORTING)
                    break

        # Leave guild
        await guild.leave()

    @commands.Cog.listener("on_member_remove")
    async def _member_remove(self, member: discord.Member):
        auto_leave = False
        async with self.config.user(member).all() as user_settings:
            if member.guild.id in user_settings["supporting_in"]:
                user_settings["supporting_in"].remove(member.guild.id)
            if not user_settings["supporting_in"] and not user_settings["end_timestamp"]:
                auto_leave = True
        if auto_leave:
            await self._initiate_autoleave(member.id)

    @commands.Cog.listener("on_member_update")
    async def _member_update(self, before: discord.Member, after: discord.Member):

        main_servers = await self.config.main_servers()
        server_roles = main_servers.get(str(after.guild.id))

        # Ignore these
        if (
                after.bot or  # Member is a bot
                await self.bot.cog_disabled_in_guild(self, after.guild) or  # Cog disabled in guild
                before.roles == after.roles or  # No role change
                not server_roles  # Not in a main server, or no roles set
        ):
            return

        messages = await self.config.messages()
        to_send: str = ""
        auto_leave = False

        before_support = await self._role_overlap(server_roles, before)
        after_support = await self._role_overlap(server_roles, after)

        # New server supporter
        if not before_support and after_support:
            async with self.config.user(after).all() as user_settings:
                if not user_settings["supporting_in"]:
                    to_send = await self._send_thanks(messages["thanks"])
                if user_settings["end_timestamp"]:
                    user_settings["end_timestamp"] = None
                if after.guild.id not in user_settings["supporting_in"]:
                    user_settings["supporting_in"].append(after.guild.id)

        # Member stopped supporting server
        elif before_support and not after_support:
            async with self.config.user(after).all() as user_settings:
                if after.guild.id in user_settings["supporting_in"]:
                    user_settings["supporting_in"].remove(after.guild.id)
                if not user_settings["supporting_in"] and not user_settings["end_timestamp"]:
                    to_send = await self._send_expire(messages["expire"])
                    auto_leave = True

        # Try sending DM
        if to_send:
            try:
                await after.send(to_send)
            except discord.HTTPException:
                pass

        if auto_leave:
            await self._initiate_autoleave(after.id)

    @staticmethod
    async def _role_overlap(supporting_roles: list, member: discord.Member):
        return bool(list(set(supporting_roles) & set(r.id for r in member.roles)))

    async def _fill_template(self, template: str):
        invite_url = await self.bot.get_cog("Core")._invite_url()
        return template.replace(
            "{invite}", f"{invite_url}"
        )

    async def _send_thanks(self, message: dict):
        if message["toggle"]:
            if not message["content"]:
                to_send = THANKS
            else:
                to_send = message["content"]
            return await self._fill_template(to_send)
        return None

    @staticmethod
    async def _send_expire(message: dict):
        if message["toggle"]:
            if not message["content"]:
                return EXPIRE
            else:
                return message["content"]
        return None

    @commands.group(name="botaccess")
    async def _bot_access(self, ctx: commands.Context):
        """BotAccess Settings"""

    @_bot_access.group(name="servers", invoke_without_command=True)
    async def _servers(self, ctx: commands.Context):
        """View and modify your current BotAccess server(s)."""
        user_settings = await self.config.user(ctx.author).all()
        if user_settings["supporting_in"]:
            await ctx.send(embed=discord.Embed(
                title="BotAccess Servers",
                description=f"{humanize_list([f'`{gu.name}` (`{g}`)' if (gu := self.bot.get_guild(g)) else f'`{g}`' for g in user_settings['servers']])}",
                color=await ctx.embed_color()
            ))
            await ctx.send_help()
        else:
            return await ctx.send(await self.config.not_supporting() or NOT_SUPPORTING)

    @_servers.command("add", require_var_positional=True)
    async def _servers_add(self, ctx: commands.Context, *servers: int):
        """Add to your allowed BotAccess server(s)."""
        async with self.config.user(ctx.author).all() as user_settings:
            if user_settings["supporting_in"]:
                if user_settings["end_timestamp"]:
                    return await ctx.send("You are no longer a supporter, and cannot add more BotAccess servers.")
                limit = await self.config.limit()
                if len(user_settings["servers"]) + len(servers) > limit:
                    return await ctx.send(f"You are limited to {limit} BotAccess servers, and already have {len(user_settings['servers'])} servers!")
                for server in servers:
                    if server not in user_settings["servers"]:
                        user_settings["servers"].append(server)
                return await ctx.tick()
            else:
                return await ctx.send(await self.config.not_supporting() or NOT_SUPPORTING)

    @_servers.command("remove", aliases=["delete"], require_var_positional=True)
    async def _servers_remove(self, ctx: commands.Context, *servers: int):
        """Remove from your allowed BotAccess server(s)."""
        main_servers = await self.config.main_servers()
        allowed = await self.config.allowed()
        async with self.config.user(ctx.author).all() as user_settings:
            if user_settings["supporting_in"]:
                for server in servers:
                    if server in user_settings["servers"]:
                        if guild := self.bot.get_guild(server):
                            if guild.id not in allowed and str(guild.id) not in main_servers.keys():
                                await guild.leave()
                        user_settings["servers"].remove(server)
                    else:
                        await ctx.send(f"`{server}` was not in your BotAccess servers!")
                return await ctx.tick()
            else:
                return await ctx.send(await self.config.not_supporting() or NOT_SUPPORTING)

    @_bot_access.command(name="invite")
    async def _invite(self, ctx: commands.Context):
        """Have the bot invite link and thank you message be resent to you."""
        settings = await self.config.user(ctx.author).all()
        if settings["supporting_in"]:
            to_send = await self._send_thanks((await self.config.messages())["thanks"])
            if to_send:
                try:
                    await ctx.author.send(to_send)
                except discord.HTTPException:
                    pass
            else:
                return await ctx.send("No invite message found. Please contact the bot owner for more details.")
        else:
            return await ctx.send(await self.config.not_supporting() or NOT_SUPPORTING)

    @commands.is_owner()
    @_bot_access.group(name="set")
    async def _owner_settings(self, ctx: commands.Context):
        """Owner-Only BotAccess Settings"""

    @_owner_settings.group(name="mainservers", invoke_without_command=True)
    async def _main_servers(self, ctx: commands.Context):
        """View and set your designated BotAccess main server(s)."""
        settings = await self.config.main_servers()
        servers = ""
        for g, d in settings.items():
            if s := self.bot.get_guild(int(g)):
                roles = []
                for r in d:
                    if ro := s.get_role(r):
                        roles.append(ro)
                servers += f"{s.name} ({s.id}): {humanize_list([r.mention for r in roles])}\n"
        await ctx.send(embed=discord.Embed(
            title="BotAccess Main Servers",
            description=servers,
            color=await ctx.embed_color()
        ))
        await ctx.send_help()

    @_main_servers.command("add", require_var_positional=True)
    async def _main_servers_add(self, ctx: commands.Context, *servers: discord.Guild):
        """Add to your allowed BotAccess main server(s)."""
        async with self.config.main_servers() as settings:
            for server in servers:
                if str(server.id) not in settings.keys():
                    settings[str(server.id)] = []
        return await ctx.tick()

    @_main_servers.command("remove", aliases=["delete"], require_var_positional=True)
    async def _main_servers_remove(self, ctx: commands.Context, *servers: discord.Guild):
        """Remove from your allowed BotAccess main server(s)."""
        async with self.config.main_servers() as settings:
            for server in servers:
                if str(server.id) in settings.keys():
                    del settings[str(server.id)]
        return await ctx.tick()

    @_main_servers.command(name="accessroles", require_var_positional=True)
    async def _access_roles(self, ctx: commands.Context, server: discord.Guild, *roles: discord.Role):
        """Set the access roles in a BotAccess main server."""
        async with self.config.main_servers() as settings:
            if str(server.id) not in settings.keys():
                return await ctx.send(f"{server.name} is not a BotAccess main server!")
            settings[str(server.id)] = [r.id for r in roles]
        return await ctx.tick()

    @_owner_settings.command(name="autoleave")
    async def _auto_leave(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether to automatically leave users' servers if they stop supporting."""
        await self.config.auto_leave.toggle.set(true_or_false)
        return await ctx.tick()

    @_owner_settings.command(name="leavedelay")
    async def _leave_delay(self, ctx: commands.Context, delay_in_hours: int):
        """Set the delay to wait before automatically leaving a BotAccess server (requires autoleave to be toggled on)."""
        if delay_in_hours < 1:
            return await ctx.send("Please enter a number greater than 0!")
        await self.config.auto_leave.delay.set(delay_in_hours)
        return await ctx.tick()

    @_owner_settings.command(name="messagetoggles")
    async def _message_toggles(self, ctx: commands.Context, thanks: bool, expire: bool):
        """Toggle whether to send the Thank You and Expiration messages."""
        await self.config.messages.thanks.toggle.set(thanks)
        await self.config.messages.expire.toggle.set(expire)
        return await ctx.tick()

    @_owner_settings.command(name="thanksmsg", require_var_positional=False)
    async def _thanks_msg(self, ctx: commands.Context, *, message: str):
        """
        Set the Thank You message to be sent to users (leave blank to use default).

        You can put `{invite}` to be replaced with my invite.
        """
        await self.config.messages.thanks.content.set(message)
        return await ctx.tick()

    @_owner_settings.command(name="expiremsg", require_var_positional=False)
    async def _expire_msg(self, ctx: commands.Context, *, message: str):
        """Set the Expiration message to be sent to users (leave blank to use default)."""
        await self.config.messages.expire.content.set(message)
        return await ctx.tick()

    @_owner_settings.command(name="notsupporting")
    async def _not_supporting(self, ctx: commands.Context, *, message: str):
        """Set the message to be sent to non-BotAccess users (leave blank to use default)."""
        await self.config.not_supporting.set(message)
        return await ctx.tick()

    @_owner_settings.group(name="allowlist", invoke_without_command=True)
    async def _allowlist(self, ctx: commands.Context):
        """View and set the BotAccess server allowlist."""
        settings = await self.config.allowed()
        await ctx.send(embed=discord.Embed(
            title="BotAccess Allowed Servers",
            description=f"{humanize_list([f'`{gu.name}` (`{g}`)' if (gu := self.bot.get_guild(g)) else f'`{g}`' for g in settings])}",
            color=await ctx.embed_color()
        ))
        await ctx.send_help()

    @_allowlist.command("add", require_var_positional=True)
    async def _allowlist_add(self, ctx: commands.Context, *servers: int):
        """Add to the BotAccess server allowlist."""
        async with self.config.allowed() as settings:
            for server in servers:
                if server not in settings:
                    settings.append(server)
        return await ctx.tick()

    @_allowlist.command("remove", aliases=["delete"], require_var_positional=True)
    async def _allowlist_remove(self, ctx: commands.Context, *servers: int):
        """Remove from the BotAccess server allowlist."""
        async with self.config.allowed() as settings:
            for server in servers:
                if server in settings:
                    settings.remove(server)
        return await ctx.tick()

    @_owner_settings.command(name="serverlimit")
    async def _server_limit(self, ctx: commands.Context, num_servers: int):
        """Set the amount of BotAccess servers a user is allowed to have."""
        if num_servers < 1:
            return await ctx.send("Please enter a number greater than 0!")
        await self.config.limit.set(num_servers)
        return await ctx.tick()

    @_owner_settings.command(name="refresh")
    async def _refresh(self, ctx: commands.Context):
        """Refresh current BotAccess supporters."""
        async with ctx.typing():
            await self._refresh_supporters()
        return await ctx.send("BotAccess supporters have been refreshed!")

    @_owner_settings.command(name="reset")
    async def _reset(self, ctx: commands.Context, user: typing.Optional[discord.User], leave_servers: bool, enter_true_to_confirm: bool):
        """Reset BotAccess settings for a user or for everything."""
        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with ctx.typing():
            to_leave: typing.List[discord.Guild] = []
            if user:
                if leave_servers:
                    servers = await self.config.user(user).servers()
                    for s in servers:
                        if se := self.bot.get_guild(s):
                            to_leave.append(se)
                await self.config.user(user).clear()
                await ctx.send(f"BotAccess settings have been reset for {user.mention}.")
            else:
                if leave_servers:
                    users = await self.config.all_users()
                    for data in users.values():
                        for s in data["servers"]:
                            if se := self.bot.get_guild(s):
                                to_leave.append(se)
                await self.config.clear_all()
                await self.config.clear_all_users()
                await ctx.send("All BotAccess settings have been reset.")

            main_servers = await self.config.main_servers()
            allowed = await self.config.allowed()
            if to_leave:
                for guild in to_leave:
                    if guild.id not in allowed and str(guild.id) not in main_servers.keys():
                        await guild.leave()
                await ctx.send(f"Finished leaving {len(to_leave)} total servers.")

    @commands.bot_has_permissions(embed_links=True)
    @_owner_settings.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View BotAccess settings."""
        settings = await self.config.all()
        await ctx.send(embed=discord.Embed(
            title="BotAccess Settings",
            description=f"""
            **Auto-Leave:** {settings["auto_leave"]["toggle"]} ({settings["auto_leave"]["delay"]}hrs)
            **Server Limit:** {settings["limit"]} servers per user
            **Allowlist:** See `{ctx.clean_prefix}botaccess set allowlist`
            **Main Servers & Access Roles:** See `{ctx.clean_prefix}botaccess set mainservers`
            **Thanks Msg ({settings["messages"]["thanks"]["toggle"]}):** {settings["messages"]["thanks"]["content"] or THANKS}
            **Expire Msg ({settings["messages"]["expire"]["toggle"]}):** {settings["messages"]["expire"]["content"] or EXPIRE}
            **Error Msg:** {settings["not_supporting"] or NOT_SUPPORTING}
            """,
            color=await ctx.embed_color()
        ))
        users = ""
        for k, v in (await self.config.all_users()).items():
            try:
                u = await self.bot.get_or_fetch_user(int(k))
                user = f"{u.mention} ({u.id})"
            except discord.HTTPException:
                user = k
            users += f"{user}: {len(v['servers'])} servers\n"
        for p in pagify(users):
            await ctx.maybe_send_embed(p)

    async def _initiate_autoleave(self, user_id: int, start_timer: bool = True):
        auto_leave = await self.config.auto_leave()
        if not auto_leave["toggle"]:
            return
        end_timestamp = (datetime.now()+timedelta(hours=auto_leave["delay"])).timestamp()
        await self.config.user_from_id(user_id).end_timestamp.set(end_timestamp)
        if start_timer:
            await self._expire_timer(user_id, end_timestamp)

    async def _refresh_supporters(self):
        main_server_settings = await self.config.main_servers()
        main_servers_list: typing.List[discord.Guild] = []
        for g in main_server_settings.keys():
            if gu := self.bot.get_guild(int(g)):
                main_servers_list.append(gu)

        original_settings = await self.config.all_users()
        original_users = [u for u in original_settings.keys()]
        await self.config.clear_all_users()
        refreshed_settings = {}
        new_users: typing.List[discord.Member] = []
        new_user_ids: typing.List[int] = []

        # Refresh settings
        for guild in main_servers_list:
            for r in main_server_settings[str(guild.id)]:
                if role := guild.get_role(r):
                    async for member in AsyncIter(role.members, steps=100):
                        if cur := refreshed_settings.get(str(member.id)):
                            cur["supporting_in"].append(guild.id)
                            refreshed_settings[str(member.id)] = {
                                "supporting_in": cur["supporting_in"],
                                "servers": cur["servers"],
                                "end_timestamp": cur["end_timestamp"]
                            }
                        elif orig := original_settings.get(member.id):
                            original_users.remove(member.id)
                            refreshed_settings[str(member.id)] = {
                                "supporting_in": [guild.id],
                                "servers": orig["servers"],
                                "end_timestamp": orig["end_timestamp"]
                            }
                        else:
                            new_users.append(member)
                            new_user_ids.append(member.id)
                            refreshed_settings[str(member.id)] = {
                                "supporting_in": [guild.id],
                                "servers": [],
                                "end_timestamp": None
                            }

        # Store to config
        async for user, settings in AsyncIter(refreshed_settings.items(), steps=50):
            async with self.config.user_from_id(int(user)).all() as cur_settings:
                cur_settings["supporting_in"] = settings["supporting_in"]
                cur_settings["servers"] = settings["servers"]
                cur_settings["end_timestamp"] = settings["end_timestamp"]

        messages = await self.config.messages()
        thanks = await self._send_thanks(messages["thanks"])
        expire = await self._send_expire(messages["expire"])

        # New users
        if thanks:
            async for user in AsyncIter(new_users, steps=100):
                try:
                    await user.send(thanks)
                except discord.HTTPException:
                    pass

        # Expired users
        async for user_id in AsyncIter(original_users, steps=100):
            try:
                user = await self.bot.get_or_fetch_user(user_id)
                if not original_settings.get(user_id)["end_timestamp"]:
                    if expire:
                        await user.send(expire)
                    await self._initiate_autoleave(user_id, start_timer=False)
            except discord.HTTPException:
                pass

    async def _expire_handler(self):
        await self.bot.wait_until_red_ready()
        await self._refresh_supporters()
        try:
            expire_coros = []
            for user, data in (await self.config.all_users()).items():
                if not data["servers"] and not data["supporting_in"] and not data["end_timestamp"]:
                    await self.config.user_from_id(int(user)).clear()
                    continue
                if data["supporting_in"] or not data["end_timestamp"]:
                    continue
                expire_coros.append(self._expire_timer(int(user), data["end_timestamp"]))
            await asyncio.gather(*expire_coros)
        except Exception:
            pass

    async def _expire_timer(self, user_id: int, end_timestamp: float):
        seconds_left = (datetime.fromtimestamp(end_timestamp) - datetime.now()).total_seconds()
        if seconds_left > 0:
            await asyncio.sleep(seconds_left)
        await self._expire_leave(user_id)

    async def _expire_leave(self, user_id: int):
        user_settings = await self.config.user_from_id(user_id).all()
        main_servers = await self.config.main_servers()
        allowed = await self.config.allowed()
        if user_settings["end_timestamp"] and not user_settings["supporting_in"]:
            if datetime.fromtimestamp(user_settings["end_timestamp"]) <= datetime.now():
                for guild in user_settings["servers"]:
                    if g := self.bot.get_guild(guild):
                        if g.id not in allowed and str(g.id) not in main_servers.keys():
                            await g.leave()
                await self.config.user_from_id(user_id).clear()
            else:
                await self._expire_timer(user_id, user_settings["end_timestamp"])

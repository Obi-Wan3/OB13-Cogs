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

import copy

import discord
from redbot.core import commands, Config
from redbot.core.utils import AsyncIter


class RoleSync(commands.Cog):
    """
    Cross-Server Role Sync on Join

    Add roles to new members if they have a certain role in another server.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "roles": {},
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_member_join")
    async def _member_join(self, member: discord.Member):
        # Ignore these
        if (
                member.bot or  # Member is a bot
                await self.bot.cog_disabled_in_guild(self, member.guild) or  # Cog disabled in guild
                not member.guild.me.guild_permissions.manage_roles  # Cannot manage roles
        ):
            return

        settings = await self.config.guild(member.guild).roles()
        for pair in settings.values():

            other_server: discord.Guild = self.bot.get_guild(pair["other_server"])
            if not other_server:
                continue

            to_check: discord.Role = other_server.get_role(pair["to_check"])
            other_member: discord.Member = other_server.get_member(member.id)
            if not to_check or not other_member or to_check not in other_member.roles:
                continue

            to_add: discord.Role = member.guild.get_role(pair["to_add"])
            if not to_add or to_add >= member.guild.me.top_role:
                continue

            if to_add not in member.roles:
                await member.add_roles(to_add, reason=f"RoleSync: user has {to_check.name} in {other_server.name}")

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="rolesync")
    async def _role_sync(self, ctx: commands.Context):
        """RoleSync Settings"""

    @commands.bot_has_permissions(manage_roles=True)
    @_role_sync.command(name="add")
    async def _add(self, ctx: commands.Context, name: str, role_to_add: discord.Role, other_server: discord.Guild, role_to_check):
        """Add a new RoleSync role pair to check."""

        # Check administrator permissions
        if not (other_member := other_server.get_member(ctx.author.id)) or not other_member.guild_permissions.administrator:
            return await ctx.send("Sorry, you have to be an Administrator in both servers to set this command.")

        # Check role hierarchy
        if role_to_add >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("That role is above you in the role hierarchy!")
        elif role_to_add >= ctx.guild.me.top_role:
            return await ctx.send("That role is above me in the role hierarchy!")

        # Get role_to_check
        other_server_ctx: commands.Context = copy.copy(ctx)
        other_server_ctx.guild = other_server
        role_to_check: discord.Role = await commands.RoleConverter().convert(other_server_ctx, role_to_check)

        # Set config
        async with self.config.guild(ctx.guild).roles() as settings:
            if name in settings.keys():
                return await ctx.send("There is already an existing role pair with that name!")

            settings[name] = {
                "to_add": role_to_add.id,
                "other_server": other_server.id,
                "to_check": role_to_check.id
            }

        return await ctx.send(f"Upon join, if a user is also in {other_server.name} and has {role_to_check.name}, they will be assigned {role_to_add.mention}.")

    @_role_sync.command(name="remove")
    async def _remove(self, ctx: commands.Context, name: str):
        """Remove a RoleSync role pair."""

        async with self.config.guild(ctx.guild).roles() as settings:
            if name not in settings.keys():
                return await ctx.send("No role pair with that name found.")

            del settings[name]

        return await ctx.tick()

    @commands.bot_has_permissions(manage_roles=True)
    @_role_sync.command(name="forcesync")
    async def _force_sync(self, ctx: commands.Context, name: str, remove_role: bool = False):
        """Force a manual check of all server members to sync roles."""

        settings = await self.config.guild(ctx.guild).roles()
        if name not in settings.keys():
            return await ctx.send("No role pair with that name found.")
        await ctx.send("Forced sync has started, this may take a while...")

        counter = 0
        to_sync = settings[name]
        other_server: discord.Guild = self.bot.get_guild(to_sync["other_server"])
        if not other_server:
            return await ctx.send(f"Server with ID {to_sync['other_server']} was not found.")

        to_check: discord.Role = other_server.get_role(to_sync["to_check"])
        to_add: discord.Role = ctx.guild.get_role(to_sync["to_add"])
        if not to_check:
            return await ctx.send(f"Role with ID {to_sync['to_check']} in {other_server.name} was not found.")
        if not to_add:
            return await ctx.send(f"Role with ID {to_sync['to_add']} was not found.")
        if to_add >= ctx.guild.me.top_role:
            return await ctx.send(f"{to_add.mention} is above me in the role hierarchy!")

        async with ctx.typing():
            async for m in AsyncIter(ctx.guild.members, steps=500):
                counter += 1
                other_member: discord.Member = other_server.get_member(m.id)
                if not other_member:
                    continue

                if to_check in other_member.roles:
                    if to_add not in m.roles:
                        await m.add_roles(to_add, reason=f"RoleSync: user has {to_check.name} in {other_server.name}")
                else:
                    if to_add in m.roles and remove_role:
                        await m.remove_roles(to_add, reason=f"RoleSync: user does not have {to_check.name} in {other_server.name}")

        return await ctx.send(f"Force synced {name} for {counter} users on this server.")

    @commands.bot_has_permissions(embed_links=True)
    @_role_sync.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View RoleSync settings."""

        async with self.config.guild(ctx.guild).roles() as settings:
            desc = ""
            for k, v in settings.items():
                to_add = ctx.guild.get_role(v["to_add"])
                other_server = self.bot.get_guild(v["other_server"])
                to_check = other_server.get_role(v["to_check"]) if other_server else None
                if to_add and other_server and to_check:
                    desc += f"**{k}:** assign {to_add.mention} if users have {to_check.name} in {other_server.name}\n"
                else:
                    del settings[k]

        return await ctx.send(embed=discord.Embed(
            title="RoleSync Settings",
            description=desc,
            color=await ctx.embed_color()
        ))

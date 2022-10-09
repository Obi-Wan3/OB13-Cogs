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

SUCCESS = "Setting updated successfully. Changes will take effect upon cog reload (`[p]reload nodms`)."


class NoDMs(commands.Cog):
    """
    Disallow DM Commands

    Disallow any commands in DMs from others, with adjustable settings.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_global = {
            "toggle": False,
            "allowed": [],
            "blocked": [],
            "message": "",
            "embed": False
        }
        self.config.register_global(**default_global)

        self.allowed = []
        self.blocked = []
        self.message = ""
        self.embed = False
        self.toggle = False

    async def initialize(self):
        settings = await self.config.all()
        self.allowed = settings['allowed']
        self.blocked = settings['blocked']
        self.message = settings['message']
        self.embed = settings['embed']
        self.toggle = settings['toggle']
        self.bot.before_invoke(self.before_invoke_hook)

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke_hook)

    # Thanks PhenoM4n4n for the before_invoke_hook idea
    async def before_invoke_hook(self, ctx: commands.Context):

        if not self.toggle or ctx.channel != ctx.author.dm_channel or ctx.author.id in ctx.bot.owner_ids or isinstance(ctx.command, commands.commands._AlwaysAvailableMixin):
            return
        # Check allowlist
        if self.allowed:
            if ctx.author.id not in self.allowed:
                await self._error_message(ctx=ctx)
                raise commands.CheckFailure()

        # Check blocklist
        elif self.blocked:
            if ctx.author.id in self.blocked:
                await self._error_message(ctx=ctx)
                raise commands.CheckFailure()

        else:
            await self._error_message(ctx=ctx)
            raise commands.CheckFailure()

    async def _error_message(self, ctx: commands.Context):
        if self.message:
            if self.embed:
                await ctx.send(embed=discord.Embed(description=self.message, color=await ctx.embed_color()))
            else:
                await ctx.send(self.message)
            return True
        return False

    @commands.is_owner()
    @commands.group(name="nodms")
    async def _no_dms(self, ctx: commands.Context):
        """
        NoDMs Settings

        Keep in mind, changes only take effect upon cog reload.
        """

    @_no_dms.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether to ignore any DM commands."""
        await self.config.toggle.set(true_or_false)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="allow")
    async def _allow(self, ctx: commands.Context, *users: discord.User):
        """Add a user to the DM command allowlist."""
        async with self.config.allowed() as allowlist:
            for u in users:
                if u.id not in allowlist:
                    allowlist.append(u.id)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="disallow")
    async def _disallow(self, ctx: commands.Context, *users: discord.User):
        """Remove a user from the DM command allowlist."""
        async with self.config.allowed() as allowlist:
            for u in users:
                if u.id in allowlist:
                    allowlist.remove(u.id)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="block")
    async def _block(self, ctx: commands.Context, *users: discord.User):
        """Add a user to the DM command blocklist."""
        async with self.config.blocked() as blocklist:
            for u in users:
                if u.id not in blocklist:
                    blocklist.append(u.id)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="unblock")
    async def _unblock(self, ctx: commands.Context, *users: discord.User):
        """Remove a user from the DM command blocklist."""
        async with self.config.blocked() as blocklist:
            for u in users:
                if u.id in blocklist:
                    blocklist.remove(u.id)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="message")
    async def _message(self, ctx: commands.Context, embed: typing.Optional[bool], *, message: str):
        """Set the error message sent to users (leave blank to remove)."""
        await self.config.message.set(message)
        await self.config.embed.set(embed)
        return await ctx.send(SUCCESS)

    @_no_dms.command(name="testmsg")
    async def _test_msg(self, ctx: commands.Context):
        """Send a test error message."""
        if not await self._error_message(ctx):
            return await ctx.send("There is no set error message for NoDMs!")

    @commands.bot_has_permissions(embed_links=True)
    @_no_dms.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the NoDms settings."""
        settings = await self.config.all()

        return await ctx.send(
            embed=discord.Embed(
                title="NoDMs Settings",
                color=await ctx.embed_color(),
                description=f"""
                **Toggle:** {settings['toggle']}
                **Embed:** {settings['embed']}
                **Message:** {settings['message'] or None}
                **Allowlist:** {' '.join([self.bot.get_user(i).mention or i for i in settings['allowed']]) if settings['allowed'] else None}
                **Blocklist:** {' '.join([self.bot.get_user(i).mention or i for i in settings['blocked']]) if settings['blocked'] else None}
                """
            )
        )

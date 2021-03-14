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

import datetime
from copy import copy

import discord
from redbot.core import commands, Config


class Counting(commands.Cog):
    """
    Counting Channel

    Create a counting channel for your server, with various additional management options!
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {"toggle": True, "channel": None, "counter": 0, "role": None, "assignrole": False, "allowrepeats": False, "penalty": (None, None), "wrong": {}}
        self.config.register_guild(**default_guild)
        self.deleted = []

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if not message.guild:
            return
        counting_channel = await self.config.guild(message.guild).channel()

        # Ignore these messages
        if (
            message.channel.id != counting_channel or  # Message not in counting channel
            await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
            not await self.config.guild(message.guild).toggle() or  # Counting toggled off
            message.author.bot or  # Message author is a bot
            counting_channel is None  # Counting channel not set
        ):
            return

        counter = await self.config.guild(message.guild).counter()
        to_delete = False
        # Delete these messages
        try:
            # Incorrect number
            if not (int(message.content.strip().split()[0])-1 == counter):
                to_delete = True

            # User repeated and allow repeats is off
            if not await self.config.guild(message.guild).allowrepeats():
                found = False
                last = message
                while not found:
                    last_m = (await message.channel.history(limit=1, before=last).flatten())[0]
                    if not last_m.author.bot:
                        found = True
                if last_m.author.id == message.author.id:
                    to_delete = True

        except ValueError:  # No number as first word of message
            to_delete = True

        if to_delete:
            self.deleted.append(message.id)
            msg_copy = copy(message)
            try:
                await message.delete()
                penalty = await self.config.guild(message.guild).penalty()
                async with self.config.guild(message.guild).wrong() as wrong:
                    try:
                        wrong[str(message.author.id)] += 1
                    except KeyError:
                        wrong[str(message.author.id)] = 1
                    if wrong[str(message.author.id)] >= penalty[0] and message.author.id != message.guild.owner.id and not message.author.guild_permissions.administrator:
                        channel_mute = self.bot.get_command("channelmute")
                        msg_copy.author = message.guild.owner
                        ctx = await self.bot.get_context(msg_copy)
                        if channel_mute:
                            await channel_mute(ctx=ctx, users=[message.author], time_and_reason={"duration": datetime.timedelta(seconds=penalty[1]), "reason": "Counting: too many wrong counts"})
                        wrong[str(message.author.id)] = 0
            except Exception:
                pass
            return

        await self.config.guild(message.guild).counter.set(counter+1)

        # Assign a role the lastest user to count if toggled
        role_id = await self.config.guild(message.guild).role()
        if await self.config.guild(message.guild).assignrole() and role_id:
            role = message.guild.get_role(role_id)
            if role is not None:
                assigned = False
                for m in role.members:
                    if m.id == message.author.id:
                        assigned = True
                    else:
                        try:
                            await m.remove_roles(role, reason="Counter: no longer the latest user to count")
                        except discord.Forbidden:
                            pass
                if not assigned:
                    try:
                        await message.author.add_roles(role, reason="Counter: latest user to count")
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener("on_message_delete")
    async def _message_deletion_listener(self, message: discord.Message):
        counting_channel = await self.config.guild(message.guild).channel()

        # Ignore these messages
        if (
                not message.guild or  # Message not in a guild
                message.channel.id != counting_channel or  # Message not in counting channel
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not await self.config.guild(message.guild).toggle() or  # Counting toggled off
                message.author.bot or  # Message author is a bot
                counting_channel is None  # Counting channel not set
        ):
            return

        # Also ignore these
        try:
            _ = int(message.content.strip())
            if message.id in self.deleted:
                return self.deleted.remove(message.id)
        except ValueError:  # Message contains non-numerical characters
            return

        c = await self.bot.get_embed_colour(message.channel)
        try:
            return await message.channel.send(embed=discord.Embed(color=c, description=f"{message.author.mention} edited or deleted [their message]({message.jump_url}). Original message: ```{message.content}```"))
        except discord.Forbidden:
            return await message.channel.send(f"{message.author.mention} edited or deleted [their message]({message.jump_url}). Original message: ```{message.content}```")

    @commands.Cog.listener("on_message_edit")
    async def _message_edit_listener(self, before: discord.Message, after: discord.Message):
        await self._message_deletion_listener(before)

    @commands.guild_only()
    @commands.mod()
    @commands.group()
    async def counting(self, ctx: commands.Context):
        """Settings for Counting"""

    @counting.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle Counting in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @counting.command(name="channel")
    async def _channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the Counting channel."""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        return await ctx.tick()

    @counting.command(name="starting")
    async def _starting(self, ctx: commands.Context, num: int):
        """Set the counter to start off with."""
        await self.config.guild(ctx.guild).counter.set(num)
        return await ctx.tick()

    @counting.command(name="role")
    async def _role(self, ctx: commands.Context, role: discord.Role):
        """Set the role to assign to the most recent user to count."""
        await self.config.guild(ctx.guild).role.set(role.id)
        return await ctx.tick()

    @counting.command(name="assignrole")
    async def _assignrole(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether to assign a role to the most recent user to count (requires add/remove role perms)."""
        if not await self.config.guild(ctx.guild).role():
            return await ctx.send(f"Please set a role first using `{ctx.clean_prefix}counting role <role>`!")
        await self.config.guild(ctx.guild).assignrole.set(true_or_false)
        return await ctx.tick()

    @counting.command(name="allowrepeats")
    async def _allow_repeats(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether users can count multiple times in a row."""
        await self.config.guild(ctx.guild).allowrepeats.set(true_or_false)
        return await ctx.tick()

    @counting.command(name="penalty")
    async def _penalty(self, ctx: commands.Context, wrong: int = None, mute_time_in_seconds: int = None):
        """Mute users for a specified amount of time if they count wrong x times in a row (leave both values empty to turn off, requires Core `mutes` to be loaded)."""
        await self.config.guild(ctx.guild).penalty.set((wrong, mute_time_in_seconds))
        return await ctx.tick()

    @counting.command(name="clear")
    async def _clear(self, ctx: commands.Context):
        """Clear & reset the current Counting settings."""
        await self.config.guild(ctx.guild).clear()
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @counting.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current Counting settings."""
        settings = await self.config.guild(ctx.guild).all()
        desc = f"""
            **Toggle:** {settings["toggle"]}
            **Channel:** {self.bot.get_channel(settings["channel"]).mention if settings["channel"] is not None else None}
            **Current #:** {settings["counter"]}
            **Role:** {ctx.guild.get_role(settings["role"]).mention if settings["role"] is not None else None}
            **Allow Repeats:** {settings["allowrepeats"]}
            **Assign Role:** {settings["assignrole"]}
            **Wrong Count Penalty:** {f'ChannelMute for {settings["penalty"][1]}s if {settings["penalty"][0]} wrong tries in a row' if settings["penalty"][0] and settings["penalty"][1] else "Not Set"}
            """
        return await ctx.send(embed=discord.Embed(title="Counting Settings", color=await ctx.embed_color(), description=desc))

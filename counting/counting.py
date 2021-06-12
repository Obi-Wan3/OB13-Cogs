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
    Multifeatured Counting Channel

    Create a counting channel for your server, with various additional management options!
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": True,
            "channel": None,
            "counter": 0,
            "role": None,
            "assignrole": False,
            "allowrepeats": False,
            "penalty": (None, None),
            "wrong": {}
        }
        default_member = {
            "counts": 0
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
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
            message.author.bot  # Message author is a bot
        ):
            return

        permissions: discord.Permissions = message.channel.permissions_for(message.guild.me)
        counter = await self.config.guild(message.guild).counter()
        to_delete = False

        # Incorrect number (delete)
        try:
            if not (int(message.content.strip().split()[0])-1 == counter):
                to_delete = True
        except ValueError:  # No number as first word of message
            to_delete = True

        # User repeated and allow repeats is off (delete)
        if not await self.config.guild(message.guild).allowrepeats() and permissions.read_message_history:
            last_m = (await message.channel.history(limit=1, before=message).flatten())[0]
            if last_m.author.id == message.author.id:
                to_delete = True

        if to_delete:
            self.deleted.append(message.id)
            msg_copy = copy(message)

            if not permissions.manage_messages:
                return

            await message.delete()

            if all(penalty := await self.config.guild(message.guild).penalty()):
                async with self.config.guild(message.guild).wrong() as wrong:
                    wrong[str(message.author.id)] = wrong.get(str(message.author.id), 0) + 1
                    if wrong[str(message.author.id)] >= penalty[0] and message.author.id != message.guild.owner.id and not message.author.guild_permissions.administrator:
                        try:
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
        async with self.config.member(message.author).all() as member_settings:
            member_settings["counts"] += 1

        # Assign a role the latest user to count if toggled
        role_id = await self.config.guild(message.guild).role()
        if await self.config.guild(message.guild).assignrole() and role_id and permissions.manage_roles:
            role = message.guild.get_role(role_id)
            if role and role < message.guild.me.top_role:
                assigned = False
                for m in role.members:
                    if m.id == message.author.id:
                        assigned = True
                    else:
                        await m.remove_roles(role, reason="Counter: no longer the latest user to count")
                if not assigned:
                    await message.author.add_roles(role, reason="Counter: latest user to count")

    @commands.Cog.listener("on_message_delete")
    async def _message_deletion_listener(self, message: discord.Message):

        # Ignore these messages
        if (
                not message.guild or  # Message not in a guild
                message.channel.id != (await self.config.guild(message.guild).channel()) or  # Message not in counting channel
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not await self.config.guild(message.guild).toggle() or  # Counting toggled off
                message.author.bot or  # Message author is a bot
                not message.channel.permissions_for(message.guild.me).send_messages  # Cannot send message
        ):
            return

        # Also ignore these
        try:
            _ = int(message.content.strip())
            if message.id in self.deleted:
                return self.deleted.remove(message.id)
        except ValueError:  # Message contains non-numerical characters
            return

        if message.channel.permissions_for(message.guild.me).embed_links:
            return await message.channel.send(embed=discord.Embed(
                color=await self.bot.get_embed_colour(message.channel),
                description=f"{message.author.mention} edited or deleted [their message]({message.jump_url}). Original message: ```{message.content}```"
            ))
        else:
            return await message.channel.send(f"{message.author.mention} edited or deleted their message. Original message: ```{message.content}```")

    @commands.Cog.listener("on_message_edit")
    async def _message_edit_listener(self, before: discord.Message, _):
        await self._message_deletion_listener(before)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="topcounters")
    async def _top_counters(self, ctx: commands.Context):
        """Show the Counting leaderboard in this server."""
        members = await self.config.all_members(ctx.guild)
        member_counts = sorted([(k, v["counts"]) for k, v in members.items()], key=lambda m: m[1], reverse=True)

        embed = discord.Embed(title="Counting Leaderboard", color=await ctx.embed_color())
        if not member_counts or member_counts[0][1] == 0:
            embed.description = "No users have counted yet."
        else:
            embed.description = "```py\nCounts | User\n"
            for member, counts in member_counts[:10]:
                embed.description += f"{str(counts).rjust(6)}   {ctx.guild.get_member(member).display_name}\n"
            embed.description += "```"
        return await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
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

    @commands.admin_or_permissions(manage_roles=True)
    @counting.command(name="role")
    async def _role(self, ctx: commands.Context, role: discord.Role):
        """Set the role to assign to the most recent user to count."""

        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("That role is above you in the role hierarchy!")
        elif role >= ctx.guild.me.top_role:
            return await ctx.send("That role is above me in the role hierarchy!")

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

    @counting.command(name="resetcounts")
    async def _reset_counts(self, ctx: commands.Context):
        """Reset the current Counting scores for all server members."""
        await self.config.clear_all_members(ctx.guild)
        return await ctx.tick()

    @counting.command(name="clear")
    async def _clear(self, ctx: commands.Context):
        """Clear & reset the current Counting settings."""
        await self.config.guild(ctx.guild).clear()
        await self.config.clear_all_members(ctx.guild)
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @counting.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current Counting settings."""
        settings = await self.config.guild(ctx.guild).all()

        channel_mention = None
        if settings["channel"] and (c := ctx.guild.get_channel(settings["channel"])):
            channel_mention = c.mention

        role_mention = None
        if settings["role"] and (r := ctx.guild.get_role(settings["role"])):
            role_mention = r.mention

        desc = f"""
            **Toggle:** {settings["toggle"]}
            **Channel:** {channel_mention}
            **Current #:** {settings["counter"]}
            **Role:** {role_mention}
            **Allow Repeats:** {settings["allowrepeats"]}
            **Assign Role:** {settings["assignrole"]}
            **Wrong Count Penalty:** {f'ChannelMute for {settings["penalty"][1]}s if {settings["penalty"][0]} wrong tries in a row' if all(settings["penalty"]) else "Not Set"}
            """

        return await ctx.send(embed=discord.Embed(title="Counting Settings", color=await ctx.embed_color(), description=desc))

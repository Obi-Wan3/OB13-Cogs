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

import re

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list


# Thanks ZeLarp for the original RegEx
URL_REGEX = r"<?https?:\/\/[^\s/$.?#].[^\s]*>?"


class EmbedReact(commands.Cog):
    """
    Auto-Reactions to Embeds

    Automatically add reactions to messages with embedded content.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": True,
            "reactions": {}
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):
        if not message.guild or not message.channel.permissions_for(message.guild.me).add_reactions:
            return

        reactions = (await self.config.guild(message.guild).reactions()).get(str(message.channel.id))

        # Ignore these messages
        if (
            await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
            not await self.config.guild(message.guild).toggle() or  # EmbedReact toggled off
            message.author.bot or  # Message author is a bot
            not reactions  # No reactions set in channel
        ):
            return

        match = re.search(URL_REGEX, message.content)
        if (
                len(message.attachments) > 0 or
                (
                        match and not (match.group(0).startswith("<") and match.group(0).endswith(">"))
                )
        ):
            for r in reactions:
                try:
                    await message.add_reaction(r)
                except (discord.HTTPException, discord.InvalidArgument):
                    pass

        return

    @commands.guild_only()
    @commands.mod()
    @commands.group()
    async def embedreact(self, ctx: commands.Context):
        """EmbedReact Settings"""

    @embedreact.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle EmbedReact in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @commands.bot_has_permissions(add_reactions=True)
    @embedreact.command(name="reactions", aliases=["emojis"])
    async def _reactions(self, ctx: commands.Context, channel: discord.TextChannel, *emojis: str):
        """Set the emojis to automatically react with for a channel."""
        for e in emojis:
            try:
                await ctx.message.add_reaction(e)
            except (discord.HTTPException, discord.InvalidArgument):
                return await ctx.send(f"Invalid emoji: {e}")
        async with self.config.guild(ctx.guild).reactions() as reactions:
            reactions[str(channel.id)] = emojis
        return await ctx.tick()

    @embedreact.command(name="remove")
    async def _remove(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Remove channels to automatically react with emojis in."""
        async with self.config.guild(ctx.guild).reactions() as reactions:
            for c in channels:
                del reactions[str(c.id)]
        return await ctx.tick()

    @embedreact.command(name="clear")
    async def _clear(self, ctx: commands.Context):
        """Clear & reset the current EmbedReact settings."""
        await self.config.guild(ctx.guild).clear()
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @embedreact.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current EmbedReact settings."""
        config = await self.config.guild(ctx.guild).all()

        embed = discord.Embed(title="EmbedReact Settings", color=await ctx.embed_color(), description=f"**Toggle:** {config['toggle']}\n{'**Reactions:** None' if not config['reactions'] else ''}")

        if config['reactions']:
            r_string = ""
            for k in config['reactions'].keys():
                try:
                    r_string += f"{self.bot.get_channel(int(k)).mention} {humanize_list(config['reactions'][k])}\n"
                except AttributeError:
                    async with self.config.guild(ctx.guild).reactions() as s:
                        del s[k]
            embed.add_field(name="Reactions", value=r_string)

        return await ctx.send(embed=embed)

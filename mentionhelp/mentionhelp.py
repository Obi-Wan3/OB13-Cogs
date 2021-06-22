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


class MentionHelp(commands.Cog):
    """
    Customizable MentionHelp Message

    Set a custom message to be sent on bot mention.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 14000605, force_registration=True)
        default_guild = {
            "toggle": True
        }
        default_global = {
            "toggle": True,
            "message": None,
            "embed": False
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):
        if (
                message.author.bot or  # Message author is a bot
                not await self.config.toggle()  # MentionHelp toggled off globally
        ):
            return

        if message.guild and (
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not await self.config.guild(message.guild).toggle()  # MentionHelp toggled off in guild
        ):
            return

        mention = re.compile(rf"<@!?{self.bot.user.id}>")
        destination = message.channel if message.guild else message.author
        if message.guild and not destination.permissions_for(message.guild.me).send_messages:
            return

        to_send = await self.config.message()

        if mention.fullmatch(message.content.strip()) and self.bot.user.id in [u.id for u in message.mentions] and to_send:
            if (await self.config.embed()) and ((not message.guild) or destination.permissions_for(message.guild.me).embed_links):
                return await destination.send(embed=discord.Embed(description=to_send, color=await self.bot.get_embed_color(destination)))
            return await destination.send(to_send)

    @commands.group(name="mentionhelp")
    async def _mention_help(self, ctx: commands.Context):
        """Send a message when a user mentions the bot (with no other text)."""

    @commands.is_owner()
    @_mention_help.command(name="message")
    async def _message(self, ctx: commands.Context, *, message: str):
        """Set the MentionHelp message."""
        await self.config.message.set(message)
        return await ctx.tick()

    @commands.is_owner()
    @_mention_help.command(name="global")
    async def _global(self, ctx: commands.Context, true_or_false: bool):
        """Toggle MentionHelp globally (an "off" server toggle overrides a global "on")."""
        await self.config.toggle.set(true_or_false)
        return await ctx.tick()

    @commands.is_owner()
    @_mention_help.command(name="embed")
    async def _embed(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether MentionHelp should use embeds."""
        await self.config.embed.set(true_or_false)
        return await ctx.tick()

    @commands.is_owner()
    @_mention_help.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the MentionHelp settings."""
        return await ctx.send(f"**Global Toggle:** {await self.config.toggle()}\n**Use Embeds:** {await self.config.embed()}\n**Message:** {await self.config.message()}")

    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @_mention_help.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle MentionHelp in this server (provided the global toggle is on)."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

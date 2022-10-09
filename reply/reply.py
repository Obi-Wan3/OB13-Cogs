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
from redbot.core import commands


class Reply(commands.Cog):
    """Bot Replies to Messages"""

    def __init__(self, bot):
        self.bot = bot

    @commands.admin_or_permissions(administrator=True)
    @commands.command(name="reply")
    async def _reply(self, ctx: commands.Context, to_mention: typing.Optional[bool], message: discord.Message, *, content: str):
        """Reply to a message using the Discord reply feature."""
        mention_author = to_mention or False
        try:
            await message.reply(content, mention_author=mention_author)
        except discord.Forbidden:
            return await ctx.send("I cannot reply to the message!")
        return await ctx.tick()

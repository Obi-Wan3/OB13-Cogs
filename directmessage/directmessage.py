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

import discord
from redbot.core import commands
import logging

log = logging.getLogger("red.obi.directmessage")


class DirectMessage(commands.Cog):
    """Send DMs as the bot!"""
   
    def cog_unload(self):
        global dm
        if dm:
            try:
                self.bot.remove_command("dm")
            except Exception as e:
                log.info(e)
            self.bot.add_command(dm)
        if self.startup_task:
            self.startup_task.cancel() 

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="dm", aliases=["sdm", "directmessage"])
    async def _dm(self, ctx: commands.Context, user: discord.User, *, message):
        """Sends a DM to a user (sends raw text directly)."""
        try:
            await user.send(message)
        except discord.Forbidden:
            await ctx.author.send(f"User does not have DMs enabled.")

def setup(bot):
    cog = DirectMessage(bot)
    global dm
    
    dm = bot.remove_command("dm")
    bot.add_cog(cog)

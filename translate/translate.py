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

import googletrans

import discord
from redbot.core import commands

TRANSLATOR = googletrans.Translator()


class Translate(commands.Cog):
    """
    Free Google Translations

    Translate some text using Google Translate for free.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translate")
    async def _translate(self, ctx: commands.Context, language, *, message):
        """Translate some text."""

        if language.lower() in googletrans.LANGUAGES:
            language = googletrans.LANGUAGES[language.lower()]
        elif language.lower() in ("zh", "ch", "chinese"):
            language = "zh-cn"

        # IF:
        # - message is a string consisting solely of digits
        # - message is a valid message id in the same channel
        # - the message that the id points to has content
        # THEN
        # - replace message with the contents of that referenced message, and call translate on its contents
        # OTHERWISE
        # - continue like we used to
        # eg
        # JKohlman sent `this is a test message` with ID 1234
        # JKohlman sent `[p]translate French 1234`
        # Bot replies with the translation `this is a test message` -> `Ceci est un message test`
        try:
            if message.isdigit():
                message_id = int(message)
                ref_message = await ctx.fetch_message(message_id)
                if ref_message.content:
                    message = ref_message.content
        except:
            pass

        try:
            res = TRANSLATOR.translate(message, dest=language)
        except (ValueError, AttributeError):
            failed_embed = discord.Embed(description="Translation failed.", color=discord.Color.red())
            return await ctx.channel.send(embed=failed_embed)

        translated_embed = discord.Embed(title='Translation', color=discord.Color.green())
        translated_embed.add_field(name=googletrans.LANGUAGES[res.src.lower()].title(), value=res.origin, inline=True)
        translated_embed.add_field(name=googletrans.LANGUAGES[res.dest.lower()].title(), value=res.text, inline=True)

        return await ctx.channel.send(embed=translated_embed)

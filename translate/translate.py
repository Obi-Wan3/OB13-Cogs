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

import typing
import functools
import googletrans, googletrans.models

import discord
from redbot.core import commands

TRANSLATOR = googletrans.Translator()
MISSING_INPUTS = "Please provide a message ID/link, some text to translate, or reply to the original message."
LANGUAGE_NOT_FOUND = "An invalid language code was provided."
TRANSLATION_FAILED = "Something went wrong while translating."


class Translate(commands.Cog):
    """
    Free Google Translations

    Translate some text using Google Translate for free.
    """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _convert_language(language: str):
        language = googletrans.LANGUAGES.get(language, language).lower()
        if language in ("zh", "ch", "chinese"):
            language = "chinese (simplified)"
        if language not in googletrans.LANGUAGES.values():
            language = None
        return language

    @staticmethod
    async def _convert_input(context: commands.Context, user_input: str):
        to_translate, to_reply = None, None

        try:
            if not user_input:
                raise commands.BadArgument

            converted_message: discord.Message = await commands.MessageConverter().convert(ctx=context, argument=user_input)

            to_translate = converted_message.content
            to_reply = converted_message

        except commands.BadArgument:

            if user_input:
                to_translate = user_input
                to_reply = context.message

            elif context.message.reference and isinstance(context.message.reference.resolved, discord.Message):
                to_translate = context.message.reference.resolved.content
                to_reply = context.message.reference.resolved

        if to_reply and to_reply.channel.id != context.channel.id:
            to_reply = context.message

        return to_translate, to_reply

    @staticmethod
    async def _result_embed(res: googletrans.models.Translated, color: discord.Color):
        embed = discord.Embed(color=color)
        embed.add_field(name=googletrans.LANGUAGES[res.src.lower()].title(), value=res.origin, inline=True)
        embed.add_field(name=googletrans.LANGUAGES[res.dest.lower()].title(), value=res.text, inline=True)
        return embed

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translate")
    async def _translate(self, ctx: commands.Context, to_language: str, *, optional_input: str):
        """
        Translate the given text to another language (auto-detect source language).

        You can provide a message ID/link, some text, or just reply to the original message.
        """

        async with ctx.typing():
            if not (to_language := await self._convert_language(to_language)):
                return await ctx.send(LANGUAGE_NOT_FOUND)

            to_translate, to_reply = await self._convert_input(ctx, optional_input)

            if not (to_translate and to_reply):
                return await ctx.send(MISSING_INPUTS)

            task = functools.partial(TRANSLATOR.translate, text=to_translate, dest=to_language)

            try:
                result: googletrans.models.Translated = await self.bot.loop.run_in_executor(None, task)
            except Exception:
                return await ctx.channel.send(embed=discord.Embed(description=TRANSLATION_FAILED, color=discord.Color.red()))

            result_embed = await self._result_embed(result, await ctx.embed_color())

        return await to_reply.reply(embed=result_embed, mention_author=False)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translatefrom")
    async def _translate_from(self, ctx: commands.Context, source_language: str, to_language: str, *, optional_input: str):
        """
        Translate the given text from a specified origin language to another language.

        You can by provide a message ID/link, some text, or just reply to the original message.
        """

        async with ctx.typing():
            if not (source_language := await self._convert_language(source_language)) or not (to_language := await self._convert_language(to_language)):
                return await ctx.send(LANGUAGE_NOT_FOUND)

            to_translate, to_reply = await self._convert_input(ctx, optional_input)

            if not (to_translate and to_reply):
                return await ctx.send(MISSING_INPUTS)

            task = functools.partial(TRANSLATOR.translate, text=to_translate, src=source_language, dest=to_language)

            try:
                result: googletrans.models.Translated = await self.bot.loop.run_in_executor(None, task)
            except Exception:
                return await ctx.channel.send(embed=discord.Embed(description=TRANSLATION_FAILED, color=discord.Color.red()))

            result_embed = await self._result_embed(result, await ctx.embed_color())

        return await to_reply.reply(embed=result_embed, mention_author=False)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="language")
    async def _language(self, ctx: commands.Context, *, optional_input: str):
        """
        Find out what language the given text is in.

        You can by provide a message ID/link, some text, or just reply to the original message.
        """
        async with ctx.typing():
            to_translate, to_reply = await self._convert_input(ctx, optional_input)

            if not (to_translate and to_reply):
                return await ctx.send(MISSING_INPUTS)

            task = functools.partial(TRANSLATOR.detect, text=to_translate)

            try:
                result: googletrans.models.Detected = await self.bot.loop.run_in_executor(None, task)
            except Exception:
                return await ctx.channel.send(embed=discord.Embed(description=TRANSLATION_FAILED, color=discord.Color.red()))

            result_embed = discord.Embed(color=await ctx.embed_color())
            result_embed.add_field(name="Language", value=googletrans.LANGUAGES[result.lang.lower()].title(), inline=True)
            result_embed.add_field(name="Confidence", value=f"{int(result.confidence*100)}%", inline=True)

        return await to_reply.reply(embed=result_embed, mention_author=False)

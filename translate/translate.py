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

import re
import typing
import functools
import googletrans, googletrans.models

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import pagify

TRANSLATOR = googletrans.Translator()
MISSING_INPUTS = "Please provide a message ID/link, some text to translate, or reply to the original message."
LANGUAGE_NOT_FOUND = "An invalid language code was provided."
TRANSLATION_FAILED = "Something went wrong while translating."

CUSTOM_EMOJI = re.compile("<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")  # Thanks R.Danny


class Translate(commands.Cog):
    """
    Free Google Translations

    Translate some text using Google Translate for free.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "auto": {},
            "auto_confidence": None
        }
        self.config.register_guild(**default_guild)

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

        return CUSTOM_EMOJI.sub("", to_translate or "").strip(), to_reply

    @staticmethod
    async def _result_embed(res: googletrans.models.Translated, color: discord.Color):
        embeds: typing.List[discord.Embed] = []
        for p in pagify(res.text, delims=["\n", " "]):
            embeds.append(discord.Embed(description=p, color=color))
        embeds[-1].set_footer(text=f"{googletrans.LANGUAGES[res.src.lower()].title()} → {googletrans.LANGUAGES[res.dest.lower()].title()}")
        return embeds

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):

        message_content = CUSTOM_EMOJI.sub("", message.content).strip()

        # Ignore these messages
        if (
                message.author.bot or  # Message sent by bot
                not message.guild or  # Message not in a guild
                not message_content or  # Message content empty
                not message.channel.permissions_for(message.guild.me).send_messages or  # No send permissions
                not message.channel.permissions_for(message.guild.me).embed_links or  # No embed permissions
                not (dest_lang := (await self.config.guild(message.guild).auto()).get(str(message.channel.id)))  # Not in auto-channel
        ):
            return

        # Detect source language
        if (confidence := await self.config.guild(message.guild).auto_confidence()) is not None:

            detect_task = functools.partial(TRANSLATOR.detect, text=message_content)
            try:
                detect_result: googletrans.models.Detected = await self.bot.loop.run_in_executor(None, detect_task)
            except Exception:
                return

            if detect_result.confidence*100 < confidence:
                return

        # Translate
        translate_task = functools.partial(TRANSLATOR.translate, text=message_content, dest=dest_lang)
        try:
            translate_result: googletrans.models.Translated = await self.bot.loop.run_in_executor(None, translate_task)
        except Exception:
            return

        # Source and dest languages and text are both different
        if translate_result.src.lower() != translate_result.dest.lower() and translate_result.origin.lower() != translate_result.text.lower():
            result_embeds = await self._result_embed(translate_result, await self.bot.get_embed_color(message.channel))
            try:
                await message.reply(embed=result_embeds[0], mention_author=False)
            except discord.HTTPException:
                await message.channel.send(embed=result_embeds[0])
            for e in result_embeds[1:]:
                await message.channel.send(embed=e)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translate")
    async def _translate(self, ctx: commands.Context, to_language: str, *, optional_input: str = ""):
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

            result_embeds = await self._result_embed(result, await ctx.embed_color())
        try:
            await to_reply.reply(embed=result_embeds[0], mention_author=False)
        except discord.HTTPException:
            await to_reply.channel.send(embed=result_embeds[0])
        for e in result_embeds[1:]:
            await to_reply.channel.send(embed=e)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translatefrom")
    async def _translate_from(self, ctx: commands.Context, source_language: str, to_language: str, *, optional_input: str = ""):
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

            result_embeds = await self._result_embed(result, await ctx.embed_color())
        try:
            await to_reply.reply(embed=result_embeds[0], mention_author=False)
        except discord.HTTPException:
            await to_reply.channel.send(embed=result_embeds[0])
        for e in result_embeds[1:]:
            await to_reply.channel.send(embed=e)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="language")
    async def _language(self, ctx: commands.Context, *, optional_input: str = ""):
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
        try:
            await to_reply.reply(embed=result_embed, mention_author=False)
        except discord.HTTPException:
            await to_reply.channel.send(embed=result_embed)

    @commands.admin_or_permissions(manage_messages=True)
    @commands.group(name="translateset")
    async def _translate_set(self, ctx: commands.Context):
        """Translate Settings"""

    @_translate_set.group(name="auto", invoke_without_command=True)
    async def _auto(self, ctx: commands.Context):
        """View and set the auto-translation channels for this server."""
        settings = await self.config.guild(ctx.guild).auto()
        description = ""
        for channel_id, language in settings.items():
            if channel := ctx.guild.get_channel(int(channel_id)):
                description += f"{channel.mention}: {language.title()}\n"
        await ctx.send(embed=discord.Embed(
            title="Auto-Translation Channels",
            description=description,
            color=await ctx.embed_color()
        ))
        await ctx.send_help()

    @_auto.command("set", require_var_positional=True)
    async def _auto_set(self, ctx: commands.Context, channel: discord.TextChannel, language: str):
        """Set an auto-translation channel."""
        if not (language := await self._convert_language(language)):
            return await ctx.send(LANGUAGE_NOT_FOUND)
        async with self.config.guild(ctx.guild).auto() as settings:
            settings[str(channel.id)] = language
        return await ctx.tick()

    @_auto.command("remove", aliases=["delete"], require_var_positional=True)
    async def _auto_remove(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Remove an auto-translation channel."""
        async with self.config.guild(ctx.guild).auto() as settings:
            for channel in channels:
                if str(channel.id) in settings.keys():
                    del settings[str(channel.id)]
        return await ctx.tick()

    @_auto.command("confidence")
    async def _auto_confidence(self, ctx: commands.Context, confidence: int = None):
        """Set the source language confidence threshold in terms of percentage (leave blank to remove)."""
        if confidence is not None and not (0 < confidence <= 100):
            return await ctx.send("Please enter a number between 0 and 100.")
        await self.config.guild(ctx.guild).auto_confidence.set(confidence)
        return await ctx.tick()

from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list, pagify
import discord
import random


class ImprovTime(commands.Cog):
    """Story improv, one word at a time."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {"toggle": True, "channel": None, "use_phrases": True, "phrase_list": [], "allow_repeats": False, "blocklist": [], "word_limit": 1}
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if not message.guild:
            return
        story_channel = await self.config.guild(message.guild).channel()

        # Ignore these messages
        if (
            message.channel.id != story_channel or  # Message not in story channel
            await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
            not await self.config.guild(message.guild).toggle() or  # ImprovTime toggled off
            message.author.bot or  # Message author is a bot
            story_channel is None  # Story channel not set
        ):
            return

        # Delete these messages
        if (
            len(message.content.strip().split()) > await self.config.guild(message.guild).word_limit() or  # Message too long
            (
                not(await self.config.guild(message.guild).allow_repeats()) and
                (await message.channel.history(limit=1, before=message).flatten())[0].author.id == message.author.id
            )  # Allow repeats is off and last message is also from same author
        ):
            return await message.delete()

        # These messages are sentence endings
        blocklist = await self.config.guild(message.guild).blocklist()
        if (
            message.content.strip().split()[-1][-1] in ["!", ".", "?"] and
            message.author.id not in blocklist
        ):
            sentence = message.content
            async for m in message.channel.history(limit=None, before=message):
                if (
                    not m.author.bot and
                    m.content.strip().split()[-1][-1] in ["!", ".", "?"] and
                    m.author.id not in blocklist
                ):
                    break
                if not m.author.bot:
                    sentence = f"{m.content} {sentence}"

            phrase_list = await self.config.guild(message.guild).phrase_list()
            if await self.config.guild(message.guild).use_phrases() and phrase_list:
                sentence = f"{random.choice(phrase_list)}\n\n{sentence}"

            if len(message.content) == 1:
                sentence = sentence[:-2] + sentence[-1]

            return await message.channel.send(sentence)

    @commands.guild_only()
    @commands.mod()
    @commands.group()
    async def improvtime(self, ctx: commands.Context):
        """Settings for ImprovTime"""

    @improvtime.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle ImprovTime in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @improvtime.command(name="channel")
    async def _channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the ImprovTime story channel."""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        return await ctx.tick()

    @improvtime.command(name="allowrepeats")
    async def _allow_repeats(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether users can send multiple messages in a row."""
        await self.config.guild(ctx.guild).allow_repeats.set(true_or_false)
        return await ctx.tick()

    @improvtime.command(name="addphrase")
    async def _addphrase(self, ctx: commands.Context, *, phrase: str):
        """Add a phrase to the phraselist."""
        async with self.config.guild(ctx.guild).phrase_list() as p:
            p.append(phrase.strip())
        return await ctx.tick()

    @improvtime.command(name="removephrase")
    async def _removephrase(self, ctx: commands.Context, phrase_index: int):
        """Remove a phrase from the phraselist (see index from current settings)."""
        async with self.config.guild(ctx.guild).phrase_list() as p:
            p.pop(phrase_index)
        return await ctx.tick()

    @improvtime.command(name="block")
    async def _block(self, ctx: commands.Context, user: discord.Member):
        """Blocks a user from ending the sentence."""
        async with self.config.guild(ctx.guild).blocklist() as b:
            b.append(user.id)
        return await ctx.tick()

    @improvtime.command(name="unblock")
    async def _unblock(self, ctx: commands.Context, user: discord.Member):
        """Unblocks a user from ending the sentence."""
        async with self.config.guild(ctx.guild).blocklist() as b:
            try:
                b.remove(user.id)
            except ValueError:
                pass
        return await ctx.tick()

    @improvtime.command(name="wordlimit")
    async def _wordlimit(self, ctx: commands.Context, num: int):
        """Set the the maximum words allowed for each story message."""
        if not num > 0:
            return await ctx.send("Please enter a positive integer.")
        await self.config.guild(ctx.guild).word_limit.set(num)
        return await ctx.tick()

    @improvtime.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current ImprovTime settings."""
        settings = await self.config.guild(ctx.guild).all()
        phrases = settings["phrase_list"]
        phrases_string = ""
        for phrase_index, phrase in enumerate(phrases):
            phrases_string += f"{phrase_index}. {phrase}\n"
        desc = f"""
            **Toggle:** {settings["toggle"]}
            **Channel:** {self.bot.get_channel(settings["channel"]).mention if settings["channel"] is not None else None}
            **Use Phrases:** {settings["use_phrases"]}
            **Word Limit:** {settings["word_limit"]}
            **Allow Repeat Messages from User:** {settings["allow_repeats"]}
            **Sentence Ending Blocklist**: {humanize_list([(await self.bot.get_or_fetch_user(u)).mention for u in settings["blocklist"]]) or "None"}
            **Prefix Phrases**:
            {phrases_string or "None"}
            """
        for p in pagify(desc):
            await ctx.send(embed=discord.Embed(title="ImprovTime Settings", color=await ctx.embed_color(), description=p))

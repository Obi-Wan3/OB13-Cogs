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
import typing

import discord
from redbot.core import commands, Config

NUMBER_REACTIONS = [
    "\N{DIGIT ZERO}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT ONE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT TWO}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT THREE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FOUR}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FIVE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SIX}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SEVEN}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT EIGHT}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT NINE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{KEYCAP TEN}",
    "\N{PERMANENT PAPER SIGN}\N{VARIATION SELECTOR-16}"
]

LETTER_REACTIONS = {
    "a": "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
    "b": "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
    "c": "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
    "d": "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
    "e": "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
    "f": "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
    "g": "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
    "h": "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
    "i": "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
    "j": "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
    "k": "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
    "l": "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
    "m": "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
    "n": "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
    "o": "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
    "p": "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
    "q": "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
    "r": "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
    "s": "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
    "t": "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    "u": "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
    "v": "\N{REGIONAL INDICATOR SYMBOL LETTER V}",
    "w": "\N{REGIONAL INDICATOR SYMBOL LETTER W}",
    "x": "\N{REGIONAL INDICATOR SYMBOL LETTER X}",
    "y": "\N{REGIONAL INDICATOR SYMBOL LETTER Y}",
    "z": "\N{REGIONAL INDICATOR SYMBOL LETTER Z}"
}

# Thanks https://gist.github.com/Vexs/a8fd95377ca862ca13fe6d0f0e42737e & R.Danny (from `?tag emoji regex` on discord.py server)
EMOJI_REGEX = "<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>|(?:\U0001f1e6[\U0001f1e8-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f2\U0001f1f4\U0001f1f6-\U0001f1fa\U0001f1fc\U0001f1fd\U0001f1ff])|(?:\U0001f1e7[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ef\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1e8[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ee\U0001f1f0-\U0001f1f5\U0001f1f7\U0001f1fa-\U0001f1ff])|(?:\U0001f1e9[\U0001f1ea\U0001f1ec\U0001f1ef\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1ff])|(?:\U0001f1ea[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ed\U0001f1f7-\U0001f1fa])|(?:\U0001f1eb[\U0001f1ee-\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1f7])|(?:\U0001f1ec[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ee\U0001f1f1-\U0001f1f3\U0001f1f5-\U0001f1fa\U0001f1fc\U0001f1fe])|(?:\U0001f1ed[\U0001f1f0\U0001f1f2\U0001f1f3\U0001f1f7\U0001f1f9\U0001f1fa])|(?:\U0001f1ee[\U0001f1e8-\U0001f1ea\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9])|(?:\U0001f1ef[\U0001f1ea\U0001f1f2\U0001f1f4\U0001f1f5])|(?:\U0001f1f0[\U0001f1ea\U0001f1ec-\U0001f1ee\U0001f1f2\U0001f1f3\U0001f1f5\U0001f1f7\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1f1[\U0001f1e6-\U0001f1e8\U0001f1ee\U0001f1f0\U0001f1f7-\U0001f1fb\U0001f1fe])|(?:\U0001f1f2[\U0001f1e6\U0001f1e8-\U0001f1ed\U0001f1f0-\U0001f1ff])|(?:\U0001f1f3[\U0001f1e6\U0001f1e8\U0001f1ea-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f4\U0001f1f5\U0001f1f7\U0001f1fa\U0001f1ff])|\U0001f1f4\U0001f1f2|(?:\U0001f1f4[\U0001f1f2])|(?:\U0001f1f5[\U0001f1e6\U0001f1ea-\U0001f1ed\U0001f1f0-\U0001f1f3\U0001f1f7-\U0001f1f9\U0001f1fc\U0001f1fe])|\U0001f1f6\U0001f1e6|(?:\U0001f1f6[\U0001f1e6])|(?:\U0001f1f7[\U0001f1ea\U0001f1f4\U0001f1f8\U0001f1fa\U0001f1fc])|(?:\U0001f1f8[\U0001f1e6-\U0001f1ea\U0001f1ec-\U0001f1f4\U0001f1f7-\U0001f1f9\U0001f1fb\U0001f1fd-\U0001f1ff])|(?:\U0001f1f9[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ed\U0001f1ef-\U0001f1f4\U0001f1f7\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1ff])|(?:\U0001f1fa[\U0001f1e6\U0001f1ec\U0001f1f2\U0001f1f8\U0001f1fe\U0001f1ff])|(?:\U0001f1fb[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ee\U0001f1f3\U0001f1fa])|(?:\U0001f1fc[\U0001f1eb\U0001f1f8])|\U0001f1fd\U0001f1f0|(?:\U0001f1fd[\U0001f1f0])|(?:\U0001f1fe[\U0001f1ea\U0001f1f9])|(?:\U0001f1ff[\U0001f1e6\U0001f1f2\U0001f1fc])|(?:\U0001f3f3\ufe0f\u200d\U0001f308)|(?:\U0001f441\u200d\U0001f5e8)|(?:[\U0001f468\U0001f469]\u200d\u2764\ufe0f\u200d(?:\U0001f48b\u200d)?[\U0001f468\U0001f469])|(?:(?:(?:\U0001f468\u200d[\U0001f468\U0001f469])|(?:\U0001f469\u200d\U0001f469))(?:(?:\u200d\U0001f467(?:\u200d[\U0001f467\U0001f466])?)|(?:\u200d\U0001f466\u200d\U0001f466)))|(?:(?:(?:\U0001f468\u200d\U0001f468)|(?:\U0001f469\u200d\U0001f469))\u200d\U0001f466)|[\u2194-\u2199]|[\u23e9-\u23f3]|[\u23f8-\u23fa]|[\u25fb-\u25fe]|[\u2600-\u2604]|[\u2638-\u263a]|[\u2648-\u2653]|[\u2692-\u2694]|[\u26f0-\u26f5]|[\u26f7-\u26fa]|[\u2708-\u270d]|[\u2753-\u2755]|[\u2795-\u2797]|[\u2b05-\u2b07]|[\U0001f191-\U0001f19a]|[\U0001f1e6-\U0001f1ff]|[\U0001f232-\U0001f23a]|[\U0001f300-\U0001f321]|[\U0001f324-\U0001f393]|[\U0001f399-\U0001f39b]|[\U0001f39e-\U0001f3f0]|[\U0001f3f3-\U0001f3f5]|[\U0001f3f7-\U0001f3fa]|[\U0001f400-\U0001f4fd]|[\U0001f4ff-\U0001f53d]|[\U0001f549-\U0001f54e]|[\U0001f550-\U0001f567]|[\U0001f573-\U0001f57a]|[\U0001f58a-\U0001f58d]|[\U0001f5c2-\U0001f5c4]|[\U0001f5d1-\U0001f5d3]|[\U0001f5dc-\U0001f5de]|[\U0001f5fa-\U0001f64f]|[\U0001f680-\U0001f6c5]|[\U0001f6cb-\U0001f6d2]|[\U0001f6e0-\U0001f6e5]|[\U0001f6f3-\U0001f6f6]|[\U0001f910-\U0001f91e]|[\U0001f920-\U0001f927]|[\U0001f933-\U0001f93a]|[\U0001f93c-\U0001f93e]|[\U0001f940-\U0001f945]|[\U0001f947-\U0001f94b]|[\U0001f950-\U0001f95e]|[\U0001f980-\U0001f991]|\u00a9|\u00ae|\u203c|\u2049|\u2122|\u2139|\u21a9|\u21aa|\u231a|\u231b|\u2328|\u23cf|\u24c2|\u25aa|\u25ab|\u25b6|\u25c0|\u260e|\u2611|\u2614|\u2615|\u2618|\u261d|\u2620|\u2622|\u2623|\u2626|\u262a|\u262e|\u262f|\u2660|\u2663|\u2665|\u2666|\u2668|\u267b|\u267f|\u2696|\u2697|\u2699|\u269b|\u269c|\u26a0|\u26a1|\u26aa|\u26ab|\u26b0|\u26b1|\u26bd|\u26be|\u26c4|\u26c5|\u26c8|\u26ce|\u26cf|\u26d1|\u26d3|\u26d4|\u26e9|\u26ea|\u26fd|\u2702|\u2705|\u270f|\u2712|\u2714|\u2716|\u271d|\u2721|\u2728|\u2733|\u2734|\u2744|\u2747|\u274c|\u274e|\u2757|\u2763|\u2764|\u27a1|\u27b0|\u27bf|\u2934|\u2935|\u2b1b|\u2b1c|\u2b50|\u2b55|\u3030|\u303d|\u3297|\u3299|\U0001f004|\U0001f0cf|\U0001f170|\U0001f171|\U0001f17e|\U0001f17f|\U0001f18e|\U0001f201|\U0001f202|\U0001f21a|\U0001f22f|\U0001f250|\U0001f251|\U0001f396|\U0001f397|\U0001f56f|\U0001f570|\U0001f587|\U0001f590|\U0001f595|\U0001f596|\U0001f5a4|\U0001f5a5|\U0001f5a8|\U0001f5b1|\U0001f5b2|\U0001f5bc|\U0001f5e1|\U0001f5e3|\U0001f5e8|\U0001f5ef|\U0001f5f3|\U0001f6e9|\U0001f6eb|\U0001f6ec|\U0001f6f0|\U0001f930|\U0001f9c0|[#|0-9]\u20e3"

NUMBER_REGEX = re.compile(r"^\(([0-9]|10|inf|infinity)-([0-9]|10|inf|infinity)\)", flags=re.IGNORECASE)
LETTER_REGEX = re.compile(r"^\(([a-z])-([a-z])\)", flags=re.IGNORECASE)


class ReactionPolls(commands.Cog):
    """
    Poll Channels w/ Auto-Reactions

    Set up poll channels in which reactions with emojis contained in messages are automatically added.
    In addition, reactions with the respective numbers and letters will be added (up to the reaction limit) when a range is input in the form of `(x-x)` at the beginning of a message.

    Range Examples:
        - `(1-10) What did you think of that event?`
        - `(A-F) What do you think your grade is?`
        - `(0-infinity) How many books have you read?`

    In that last example, the reactions for the numbers 0-10 would be added, then the infinity emoji (`inf` can also be written instead).
    Note: this currently does not support skin tones due to the Unicode mess that creates for regular expression matching.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {"toggle": True, "channels": {}}
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if not message.guild:
            return

        settings = await self.config.guild(message.guild).all()
        ch_settings = settings["channels"].get(str(message.channel.id))

        # Ignore these messages
        if (
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not settings["toggle"] or  # ReactionPolls toggled off
                message.author.bot or  # Message author is a bot
                not ch_settings or  # Message not in a ReactionPoll channel
                not settings["channels"][str(message.channel.id)]["toggle"] or  # ReactionPoll channel toggled off
                not message.channel.permissions_for(message.guild.me).add_reactions  # Cannot add reactions
        ):
            return

        m = message.content
        numbers = re.match(NUMBER_REGEX, m)
        letters = re.match(LETTER_REGEX, m)
        emojis = re.findall(EMOJI_REGEX, m)

        nothing = True
        reactions_to_add = []

        # Number range was included
        if numbers:
            nothing = False

            start = int(numbers.group(1)) if not numbers.group(1).startswith("inf") else 11
            end = int(numbers.group(2)) if not numbers.group(2).startswith("inf") else 11

            if start <= end:
                for i in range(start, end + 1, 1):
                    reactions_to_add.append(NUMBER_REACTIONS[i])
            else:
                for i in range(start, end - 1, -1):
                    reactions_to_add.append(NUMBER_REACTIONS[i])

        # Letter range was included
        if letters:
            nothing = False

            start = ord(letters.group(1))
            end = ord(letters.group(2))

            if start <= end:
                for i in range(start, end + 1, 1):
                    reactions_to_add.append(LETTER_REACTIONS[chr(i)])
            else:
                for i in range(start, end - 1, -1):
                    reactions_to_add.append(LETTER_REACTIONS[chr(i)])

        # Emojis were detected in message content
        if emojis:
            nothing = False
            
            for e in emojis:
                reactions_to_add.append(e)

        # None of the above was included, use defaults
        if nothing:
            for e in ch_settings["defaults"]:
                reactions_to_add.append(e)

        # Allow up to 20 reactions to try adding
        if len(reactions_to_add) > 20:
            reactions_to_add = reactions_to_add[:20]

        # Add reactions
        for r in reactions_to_add:
            try:
                await message.add_reaction(r)
            except discord.HTTPException:
                pass

    @commands.Cog.listener("on_message_edit")
    async def _edit_listener(self, before, after):
        await self._message_listener(after)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.group(name="reactionpolls", aliases=["rpolls"])
    async def _reaction_polls(self, ctx: commands.Context):
        """Settings for ReactionPolls"""

    @_reaction_polls.command(name="setchannel")
    async def _set_channel(self, ctx: commands.Context, channel: discord.TextChannel, *default_emojis: str):
        """Set a ReactionPoll channel and its default emojis (e.g. thumbs-up and down) for messages where no auto-reactions were detected."""

        for emoji in default_emojis:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                return await ctx.send(f"There was an error adding a test reaction for: {emoji}")

        async with self.config.guild(ctx.guild).channels() as settings:
            settings[str(channel.id)] = {
                "toggle": True,
                "defaults": default_emojis
            }

        return await ctx.send(f"{channel.mention} has been added as a ReactionPoll channel for this server.")

    @_reaction_polls.command(name="removechannel")
    async def _remove_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a ReactionPoll channel."""

        async with self.config.guild(ctx.guild).channels() as settings:
            if str(channel.id) not in settings.keys():
                return await ctx.send(f"{channel.mention} is not a set ReactionPoll channel!")

            del settings[str(channel.id)]

        return await ctx.send(f"{channel.mention} is not longer a ReactionPoll channel for this server.")

    @_reaction_polls.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], true_or_false: bool):
        """Toggle any or all ReactionPoll channel(s)."""

        if not channel:
            await self.config.guild(ctx.guild).toggle.set(true_or_false)

        else:
            async with self.config.guild(ctx.guild).channels() as settings:
                if str(channel.id) not in settings.keys():
                    return await ctx.send(f"{channel.mention} is not a set ReactionPoll channel!")

                settings[str(channel.id)]["toggle"] = true_or_false

        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_reaction_polls.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current settings for ReactionPolls."""

        async with self.config.guild(ctx.guild).channels() as channels:

            embed = discord.Embed(
                title="Settings for ReactionPolls",
                description=f"**Toggle:** {await self.config.guild(ctx.guild).toggle()}\n\n",
                color=await ctx.embed_color()
            )

            for ch, ch_set in channels.items():
                if channel := ctx.guild.get_channel(int(ch)):
                    embed.description += f"{channel.mention} ({ch_set['toggle']}): {' '.join(ch_set['defaults']) if ch_set['defaults'] else None}\n"
                else:
                    del channels[ch]

        return await ctx.send(embed=embed)

from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord
import re

URL_REGEX = r"<?(https?|ftp)://[^\s/$.?#].[^\s]*>?"


class EmbedReact(commands.Cog):
    """Automatic Reactions to Embedded Images"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": True,
            "reactions": [],
            "channels": []
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):
        channels = await self.config.guild(message.guild).channels()
        reactions = await self.config.guild(message.guild).reactions()

        # Ignore these messages
        if (
            message.channel.id not in channels or  # Message not in the set channels
            await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
            not await self.config.guild(message.guild).toggle() or  # EmbedReact toggled off
            message.author.bot or  # Message author is a bot
            not reactions  # No reactions set
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
                except (discord.Forbidden, discord.HTTPException, discord.NotFound, discord.InvalidArgument):
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

    @embedreact.command(name="reactions", aliases=["emojis"])
    async def _reactions(self, ctx: commands.Context, *emojis: str):
        """Set the emojis to automatically react with."""
        for e in emojis:
            try:
                await ctx.react_quietly(e)
            except (discord.Forbidden, discord.HTTPException, discord.NotFound, discord.InvalidArgument):
                return await ctx.send(f"Invalid emoji: {e}")
        await self.config.guild(ctx.guild).reactions.set(emojis)
        return await ctx.tick()

    @embedreact.command(name="channels")
    async def _channels(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Set the channels to automatically react with emojis in."""
        await self.config.guild(ctx.guild).channels.set([c.id for c in channels])
        return await ctx.tick()

    @embedreact.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current EmbedReact settings."""
        config = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="EmbedReact Settings", color=await ctx.embed_color(), description=f"""
            **Toggle:** {config['toggle']}
            **Reactions:** {' '.join(config['reactions']) if config['reactions'] else None}
            **Channels:** {humanize_list([self.bot.get_channel(c).mention for c in config['channels']]) if config['channels'] else None}
        """)
        return await ctx.send(embed=embed)

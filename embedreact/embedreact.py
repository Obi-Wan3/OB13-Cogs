from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord
import re

# Thanks ZeLarp for the RegEx
URL_REGEX = r"<?(https?|ftp)://[^\s/$.?#].[^\s]*>?"


class EmbedReact(commands.Cog):
    """Automatic Reactions to Embedded Images"""

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
        if not message.guild:
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
    async def _reactions(self, ctx: commands.Context, channel: discord.TextChannel, *emojis: str):
        """Set the emojis to automatically react with for a channel."""
        for e in emojis:
            try:
                await ctx.message.add_reaction(e)
            except (discord.Forbidden, discord.HTTPException, discord.NotFound, discord.InvalidArgument):
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

    @embedreact.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the current EmbedReact settings."""
        config = await self.config.guild(ctx.guild).all()

        embed = discord.Embed(title="EmbedReact Settings", color=await ctx.embed_color(), description=f"**Toggle:** {config['toggle']}\n{'**Reactions:** None' if not config['reactions'] else ''}")

        if config['reactions']:
            r_string = ""
            for k in config['reactions'].keys():
                r_string += f"{self.bot.get_channel(int(k)).mention} {humanize_list(config['reactions'][k])}\n"
            embed.add_field(name="Reactions", value=r_string)

        return await ctx.send(embed=embed)

from redbot.core import commands, Config
import discord
import re


class MentionHelp(commands.Cog):
    """Custom Message on Bot Mention"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 14000605, force_registration=True)
        default_guild = {
            "toggle": True
        }
        default_global = {
            "toggle": True,
            "message": None,
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):
        if (
            message.author.bot or  # Message author is a bot
            (message.guild and await self.bot.cog_disabled_in_guild(self, message.guild)) or  # Cog disabled in guild
            not await self.config.toggle() or  # MentionHelp toggled off globally
            not await self.config.guild(message.guild).toggle()  # MentionHelp toggled off in guild
        ):
            return

        mention = re.compile(rf"<@!?{self.bot.user.id}>")
        destination = message.channel if message.guild else message.author
        to_send = await self.config.message()

        if mention.fullmatch(message.content) and self.bot.user.id in [u.id for u in message.mentions] and to_send:
            await destination.send(to_send)

        return

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
    @_mention_help.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the MentionHelp settings."""
        return await ctx.send(f"**Global Toggle:** {await self.config.toggle()}\n**Message:** {await self.config.message()}")

    @commands.admin()
    @commands.guild_only()
    @_mention_help.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle MentionHelp in this server (provided the global toggle is on)."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

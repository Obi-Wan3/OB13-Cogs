from redbot.core import commands, Config
import discord
import aiohttp
import typing
import re


class BrainShop(commands.Cog):
    """
    AI Chatbot Using BrainShop

    An artificial intelligence chatbot using BrainShop (https://brainshop.ai/).
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605)
        default_global = {"auto": True}
        default_guild = {"auto": True, "channels": []}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @staticmethod
    async def _get_response(bid, key, uid, msg):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.brainshop.ai/get?bid={bid}&key={key}&uid={uid}&msg={msg}") as resp:
                if resp.status != 200:
                    return "Something went wrong while accessing the BrainShop API."
                js = await resp.json()
                return js["cnt"]

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):
        in_auto_channel = False
        if (
                message.author.bot or  # Message author is a bot
                not message.content.startswith((f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"))
        ):
            if not message.author.bot and message.guild and message.channel.id in await self.config.guild(message.guild).channels():
                in_auto_channel = True
            else:
                return

        if message.guild:
            if (
                    await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                    (not await self.config.guild(message.guild).auto() and not in_auto_channel)  # Auto reply is off
            ):
                return
        elif not await self.config.auto():  # Global auto reply turned off
            return

        async with message.channel.typing():
            brainshop_api = await self.bot.get_shared_api_tokens("brainshop")
            bid = brainshop_api.get("bid")
            key = brainshop_api.get("key")

            if not bid or not key:
                return

            filtered = re.sub(f"<@!?{self.bot.user.id}>", "", message.content)
            if not filtered:
                return

            response = await self._get_response(bid=bid, key=key, uid=message.author.id, msg=filtered)

        try:
            if hasattr(message, "reply"):
                return await message.reply(response, mention_author=False)
            return await message.channel.send(response)
        except (discord.HTTPException, discord.Forbidden, discord.InvalidArgument):
            pass

    @commands.command(name="brainshop")
    async def _brainshop(self, ctx: commands.Context, *, message: str):
        """Converse with the BrainShop AI!"""

        async with ctx.typing():
            brainshop_api = await self.bot.get_shared_api_tokens("brainshop")
            bid = brainshop_api.get("bid")
            key = brainshop_api.get("key")

            if not bid or not key:
                return await ctx.send("The BrainShop API has not been set up yet!")

            response = await self._get_response(bid=bid, key=key, uid=ctx.author.id, msg=message)

        if hasattr(ctx.message, "reply"):
            return await ctx.reply(response, mention_author=False)
        return await ctx.send(response)

    @commands.group(name="brainshopset")
    async def _brainshopset(self, ctx: commands.Context):
        """BrainShop Settings"""

    @commands.guild_only()
    @commands.admin()
    @_brainshopset.command(name="auto")
    async def _auto(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether BrainShop should automatically reply to all messages in the server starting with the bot mention."""
        await self.config.guild(ctx.guild).auto.set(true_or_false)
        return await ctx.tick()

    @commands.guild_only()
    @commands.admin()
    @_brainshopset.command(name="channels")
    async def _channels(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Set automatic reply channels for BrainShop (leave blank to remove all)."""
        if channels:
            await self.config.guild(ctx.guild).channels.set([c.id for c in channels])
        else:
            await self.config.guild(ctx.guild).channels.set([])
        return await ctx.tick()

    @commands.is_owner()
    @_brainshopset.command(name="globalauto")
    async def _global_auto(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether BrainShop should automatically reply to all messages in DMs starting with the bot mention."""
        await self.config.auto.set(true_or_false)
        return await ctx.tick()

    @commands.is_owner()
    @_brainshopset.command(name="view")
    async def _view(self, ctx: commands.Context):
        """
        View the settings for BrainShop.

        **Instructions:** Before being able to use this cog, you must do the following steps:
        1. Create a free account at https://brainshop.ai/
        2. Follow the instructions to set up your account (for domain name, use anything random, e.g. `example.com`)
        3. After creating the account, at https://brainshop.ai/user click on `Add Brain` at the left.
        4. Give the brain a title, keep all defaults and click `Save`.
        5. In the `Settings` tab for the brain, you will find the `Brain ID` and `API Key`. Copy those and use them in the following command (no brackets):
        ```
        [p]set api brainshop key,[API Key] bid,[Brain ID]
        ```
        6. You're all set! If you would like, toggle whether BrainShop should automatically reply to messages starting with a mention.
        """

        brainshop_api = await self.bot.get_shared_api_tokens("brainshop")

        embed = discord.Embed(
            title="BrainShop Settings",
            color=await ctx.embed_color(),
            description=f"""
            **Global Toggle:** {await self.config.auto()}
            **Brain ID**: {brainshop_api.get("bid") if brainshop_api.get("bid") else "Not set (see this command's help message)."}
            **API Key**: {f"||{brainshop_api.get('key')}||" if brainshop_api.get("key") else "Not set (see this command's help message)."}
            """
        )
        embed.set_footer(text="Powered by BrainShop | https://brainshop.ai/")

        return await ctx.author.send(embed=embed)

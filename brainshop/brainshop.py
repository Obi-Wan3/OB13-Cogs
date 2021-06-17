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
import aiohttp

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list

BRAINSHOP_ERROR = "Something went wrong while accessing the BrainShop API."
BRAINSHOP_TIMEOUT = "The BrainShop API timed out; please try again later."


class BrainShop(commands.Cog):
    """
    AI Chatbot Using BrainShop

    An artificial intelligence chatbot using BrainShop (https://brainshop.ai/).
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605)
        default_global = {
            "auto": True
        }
        default_guild = {
            "auto": True,
            "channels": [],
            "allowlist": [],
            "blocklist": []
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @staticmethod
    async def _get_response(bid, key, uid, msg):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.brainshop.ai/get?bid={bid}&key={key}&uid={uid}&msg={msg}") as resp:
                if resp.status != 200:
                    return BRAINSHOP_ERROR
                try:
                    js = await resp.json()
                    return js["cnt"]
                except Exception:  # likely JSONDecodeError
                    if (await resp.text()) == "(Time out)":
                        return BRAINSHOP_TIMEOUT
                    return BRAINSHOP_ERROR

    @commands.Cog.listener("on_message_without_command")
    async def _message_listener(self, message: discord.Message):

        # Ignore bots
        if message.author.bot:
            return

        global_auto = await self.config.auto()
        starts_with_mention = message.content.startswith((f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"))

        # Command is in DMs
        if not message.guild:

            if not starts_with_mention or not global_auto:
                return

        # Command is in a server
        else:

            # Cog is disabled or bot cannot send messages in channel
            if await self.bot.cog_disabled_in_guild(self, message.guild) or not message.channel.permissions_for(message.guild.me).send_messages:
                return

            guild_settings = await self.config.guild(message.guild).all()

            # Not in auto-channel
            if message.channel.id not in guild_settings["channels"]:
                if (
                        not starts_with_mention or  # Does not start with mention
                        not (guild_settings["auto"] or global_auto)  # Both guild & global auto are toggled off
                ):
                    return

            # Check block/allow-lists
            if (
                    (guild_settings["allowlist"] and message.channel.id not in guild_settings["allowlist"]) or  # Channel not in allowlist
                    (guild_settings["blocklist"] and message.channel.id in guild_settings["blocklist"])  # Channel in blocklist
            ):
                return

        # Get BrainShop api key
        brainshop_api = await self.bot.get_shared_api_tokens("brainshop")
        if not (bid := brainshop_api.get("bid")) or not (key := brainshop_api.get("key")):
            return

        # Remove bot mention
        filtered = re.sub(f"<@!?{self.bot.user.id}>", "", message.content)
        if not filtered:
            return

        # Get response from BrainShop
        async with message.channel.typing():
            response = await self._get_response(bid=bid, key=key, uid=message.author.id, msg=filtered)

        # Reply or send response
        if hasattr(message, "reply"):
            return await message.reply(response, mention_author=False)
        return await message.channel.send(response)

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
    @commands.admin_or_permissions(administrator=True)
    @_brainshopset.command(name="auto")
    async def _auto(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether BrainShop should automatically reply to all messages in the server starting with the bot mention."""
        await self.config.guild(ctx.guild).auto.set(true_or_false)
        return await ctx.tick()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @_brainshopset.command(name="autochannels")
    async def _auto_channels(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Set the automatic reply channels for BrainShop (leave blank to remove all)."""
        if channels:
            await self.config.guild(ctx.guild).channels.set([c.id for c in channels])
        else:
            await self.config.guild(ctx.guild).channels.set([])
        return await ctx.tick()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @_brainshopset.command(name="allowlist")
    async def _allowlist(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Set the BrainShop channel allowlist (leave blank to remove all)."""
        if channels:
            await self.config.guild(ctx.guild).allowlist.set([c.id for c in channels])
        else:
            await self.config.guild(ctx.guild).allowlist.set([])
        return await ctx.tick()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @_brainshopset.command(name="blocklist")
    async def _blocklist(self, ctx: commands.Context, *channels: discord.TextChannel):
        """Set the BrainShop channel blocklist (leave blank to remove all)."""
        if channels:
            await self.config.guild(ctx.guild).blocklist.set([c.id for c in channels])
        else:
            await self.config.guild(ctx.guild).blocklist.set([])
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @_brainshopset.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the server settings for BrainShop."""
        async with self.config.guild(ctx.guild).all() as guild_settings:
            setting_channels = {"channels": [], "blocklist": [], "allowlist": []}
            for ch_type in setting_channels.keys():
                for c in guild_settings[ch_type]:
                    if ch := ctx.guild.get_channel(c):
                        setting_channels[ch_type].append(ch)
                    else:
                        guild_settings[ch_type].remove(c)

            settings = f"**Mention Reply:** {guild_settings['auto']}\n"
            settings += f"**Auto-Channels:** {humanize_list(setting_channels['channels']) or None}\n"
            settings += f"**Allowlist:** {humanize_list(setting_channels['allowlist']) or None}\n"
            settings += f"**Blocklist:** {humanize_list(setting_channels['blocklist']) or None}"

        embed = discord.Embed(
            title="BrainShop Settings",
            color=await ctx.embed_color(),
            description=settings
        )
        embed.set_footer(text="Powered by BrainShop | https://brainshop.ai/")

        return await ctx.send(embed=embed)

    @commands.is_owner()
    @_brainshopset.command(name="globalauto")
    async def _global_auto(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether BrainShop should automatically reply to all messages in DMs starting with the bot mention."""
        await self.config.auto.set(true_or_false)
        return await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @_brainshopset.command(name="setup")
    async def _setup(self, ctx: commands.Context):
        """View the required BrainShop setup instructions."""
        instructions = discord.Embed(
            title="BrainShop Setup Instructions",
            description="Before being able to use this cog, you must complete the following steps:",
            color=await ctx.embed_color()
        )
        instructions.add_field(
            name="1. Create an Account",
            value="Create a free account at https://brainshop.ai/ by clicking `Sign Up`.",
            inline=False
        )
        instructions.add_field(
            name="2. Setup Your Account",
            value="Follow the instructions to set up your account. Anything works for the domain name (e.g. `example.com`).",
            inline=False
        )
        instructions.add_field(
            name='3. Add a "Brain"',
            value="Go to https://brainshop.ai/user and click on `Add Brain` at the left.",
            inline=False
        )
        instructions.add_field(
            name="4. Save Changes",
            value="Give the brain a title, keeping all defaults, and click `Save`.",
            inline=False
        )
        instructions.add_field(
            name="5. Set API Key and Brain ID",
            value=f"In the `Settings` tab for the brain, you will find the `API Key` and `Brain ID`. Copy those and use them in the following command (no brackets): ```css\n{ctx.clean_prefix}set api brainshop key [API Key] bid [Brain ID]```",
            inline=False
        )
        instructions.add_field(
            name="6. Additional Customization",
            value=f"If you would like to customize your BrainShop AI, read through their documentation. For example, follow the instructions at http://brainshop.ai/node/274434 for naming the AI, and also see https://brainshop.ai/node/277098 for customizing attributes.",
            inline=False
        )
        instructions.add_field(
            name="7. Finish Setup",
            value=f"You're all set! If you would like, toggle whether BrainShop should automatically reply to messages starting with a mention. All settings are under `{ctx.clean_prefix}brainshopset`.",
            inline=False
        )
        return await ctx.send(embed=instructions)

    @commands.is_owner()
    @_brainshopset.command(name="viewglobal")
    async def _view_global(self, ctx: commands.Context, show_api_key: bool = False):
        """View the global settings for BrainShop."""

        brainshop_api = await self.bot.get_shared_api_tokens("brainshop")

        embed = discord.Embed(
            title="BrainShop Settings",
            color=await ctx.embed_color(),
            description=f"""
            **Global Toggle:** {await self.config.auto()}
            **Brain ID**: {brainshop_api.get("bid") if brainshop_api.get("bid") else f"Not set (see `{ctx.clean_prefix}brainshopset setup`)."}
            """
        )

        if show_api_key:
            embed.description += f"""**API Key**: {f"||{brainshop_api.get('key')}||" if brainshop_api.get("key") else f"Not set (see `{ctx.clean_prefix}brainshopset setup`)."}"""

        embed.set_footer(text="Powered by BrainShop | https://brainshop.ai/")

        await ctx.tick()
        return await ctx.author.send(embed=embed)

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

import asyncio
from datetime import datetime, timezone

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list


class MessageNotifier(commands.Cog):
    """
    Notify You of Messages in Certain Channels

    Notify you of new messages in certain channels within time intervals.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_global = {
            "mention": False,
            "minutes": 3,
        }
        default_guild = {
            "channels": {},
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if (
                not message.guild or  # Not in a server
                message.author.bot or  # Message author is a bot
                await self.bot.cog_disabled_in_guild(self, message.guild)  # Cog disabled in guild
        ):
            return

        guild_settings = await self.config.guild(message.guild).channels()
        if not (channel_settings := guild_settings.get(str(message.channel.id))):
            return

        if message.author.id == channel_settings["user"]:
            async with self.config.guild(message.guild).channels() as settings:
                settings[str(message.channel.id)]["last_activity"] = datetime.now(tz=timezone.utc).timestamp()
                settings[str(message.channel.id)]["alerted"] = False
        else:
            if not (member := message.guild.get_member(channel_settings["user"])):
                return
            if not message.channel.permissions_for(member).read_message_history:
                return
            if not (alert_guild := self.bot.get_guild(channel_settings["alert_guild"])):
                return
            if not (alert_channel := alert_guild.get_channel(channel_settings["alert_channel"])):
                return
            if not (m := alert_guild.get_member(channel_settings["user"])):
                return
            if not alert_channel.permissions_for(m).read_message_history:
                return
            if not (alert_channel.permissions_for(alert_guild.me).send_messages and alert_channel.permissions_for(alert_guild.me).embed_links):
                return

            time_passed: int = int(datetime.now(tz=timezone.utc).timestamp() - channel_settings["last_activity"])
            minutes = await self.config.minutes()
            if time_passed < 60*minutes:
                await asyncio.sleep(60*minutes - time_passed)

            async with self.config.guild(message.guild).channels() as settings:

                if not (channel_settings := settings.get(str(message.channel.id))):
                    return

                if not channel_settings["alerted"] and channel_settings["last_activity"] < message.created_at.replace(tzinfo=timezone.utc).timestamp():

                    embed = discord.Embed(
                        description=f"New [message]({message.jump_url}) in {message.channel.mention} from {message.author.name}#{message.author.discriminator}",
                        color=await self.bot.get_embed_color(message.channel)
                    )

                    if await self.config.mention():
                        await alert_channel.send(f"{m.mention}", embed=embed)
                    else:
                        await alert_channel.send(embed=embed)

                    settings[str(message.channel.id)]["alerted"] = True

    @commands.Cog.listener("on_raw_reaction_add")
    async def _reaction_listener(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        guild_settings = await self.config.guild_from_id(payload.guild_id).channels()
        if not (channel_settings := guild_settings.get(str(payload.channel_id))):
            return

        if payload.member.id == channel_settings["user"]:
            async with self.config.guild_from_id(payload.guild_id).channels() as settings:
                settings[str(payload.channel_id)]["last_activity"] = datetime.now(tz=timezone.utc).timestamp()
                settings[str(payload.channel_id)]["alerted"] = False

    @commands.is_owner()
    @commands.group(name="messagenotifier")
    async def _message_notifier(self, ctx: commands.Context):
        """MessageNotifier Settings"""

    @_message_notifier.command(name="add")
    async def _add(self, ctx: commands.Context, listen_in: discord.TextChannel, alert_in_server: discord.Guild, alert_in_channel: int, user_to_alert: discord.Member):
        """Add a MessageNotifier alert on a channel's messages."""
        if not ((m := alert_in_server.get_member(user_to_alert.id)) and (c := alert_in_server.get_channel(alert_in_channel)) and (c.permissions_for(m).read_message_history)):
            return await ctx.send("That user is not in the alert server, the channel doesn't exist, or they don't have permission to view messages in that channel!")

        async with self.config.guild(listen_in.guild).channels() as settings:
            if str(listen_in.id) in settings.keys():
                return await ctx.send("There is already a MessageNotifier for that channel!")

            settings[str(listen_in.id)] = {
                "user": user_to_alert.id,
                "alert_guild": alert_in_server.id,
                "alert_channel": alert_in_channel,
                "last_activity": datetime.now(tz=timezone.utc).timestamp(),
                "alerted": False
            }

        return await ctx.tick()

    @_message_notifier.command(name="remove")
    async def _remove(self, ctx: commands.Context, listen_in: discord.TextChannel):
        """Remove a MessageNotifier alert on a channel's messages."""
        async with self.config.guild(listen_in.guild).channels() as settings:
            if str(listen_in.id) not in settings.keys():
                return await ctx.send("There is no MessageNotifier for that channel!")
            del settings[str(listen_in.id)]
        return await ctx.tick()

    @_message_notifier.command(name="mention")
    async def _mention(self, ctx: commands.Context, true_or_false: bool):
        """Toggle MessageNotifier alert mentions."""
        await self.config.mention.set(true_or_false)
        return await ctx.tick()

    @_message_notifier.command(name="interval")
    async def _interval(self, ctx: commands.Context, minutes: int):
        """Set MessageNotifier interval (in minutes) to wait."""
        if minutes < 1:
            return await ctx.send("Please enter a positive integer!")
        await self.config.minutes.set(minutes)
        return await ctx.tick()

    @_message_notifier.command(name="read")
    async def _read(self, ctx: commands.Context, channel: discord.TextChannel):
        """Mark a MessageNotifier channel as read."""
        async with self.config.guild(channel.guild).channels() as settings:
            if str(channel.id) not in settings.keys():
                return await ctx.send("That is not a MessageNotifier channel!")
            settings[str(channel.id)]["last_activity"] = datetime.now(tz=timezone.utc).timestamp()
            settings[str(channel.id)]["alerted"] = False
        return await ctx.tick()

    @_message_notifier.command(name="unread")
    async def _unread(self, ctx: commands.Context, channel: discord.TextChannel):
        """Mark a MessageNotifier channel as unread."""
        async with self.config.guild(channel.guild).channels() as settings:
            if str(channel.id) not in settings.keys():
                return await ctx.send("That is not a MessageNotifier channel!")
            settings[str(channel.id)]["alerted"] = True
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_message_notifier.command(name="view")
    async def _view(self, ctx: commands.Context, server: discord.Guild = None):
        """View the MessageNotifiers in this server."""
        global_config = await self.config.all()
        settings_server = server or ctx.guild
        if not settings_server:
            return await ctx.send("Please run this command in a server or specify one as the `server` parameter!")
        settings = await self.config.guild(settings_server).channels()
        channels = []
        for c in settings.keys():
            if ch := settings_server.get_channel(int(c)):
                channels.append(ch.mention)
        return await ctx.send(embed=discord.Embed(
            title="MessageNotifier Settings",
            description=f"**Mention:** {global_config['mention']}\n**Minutes:** {global_config['minutes']}\n**Watching Channels:** {humanize_list(channels) if channels else None}",
            color=await ctx.embed_color()
        ))

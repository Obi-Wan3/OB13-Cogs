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

import time
import aiohttp
import asyncio
from datetime import datetime

import discord
from discord.ext import tasks
from redbot.core import commands, Config


class SiteStatus(commands.Cog):
    """
    Monitor Website Statuses

    Monitor the statuses of websites and receive down alerts.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 14000605, force_registration=True)
        default_guild = {
            "sites": {}
        }
        self.config.register_guild(**default_guild)
        self._fetch_statuses.start()

    def cog_unload(self):
        self._fetch_statuses.cancel()

    @commands.command(name="getstatus")
    async def _get_status(self, ctx: commands.Context, url: str):
        """Get the current status of a website."""
        await ctx.trigger_typing()
        try:
            if url[0] == "<" and url[-1] == ">":
                url = url[1:-1]
            async with aiohttp.ClientSession() as session:
                start = time.perf_counter()
                async with session.head(url) as response:
                    return await ctx.maybe_send_embed(f"Site returned status `{response.status} {response.reason}` with latency `{round(time.perf_counter() - start, 1)}`s.")
        except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
            return await ctx.send("There was an error connecting to this site. Is the url valid?")

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="sitestatus")
    async def _site_status(self, ctx: commands.Context):
        """Monitor the Statuses of Websites"""

    @_site_status.command(name="add")
    async def _site_status_add(self, ctx: commands.Context, sitename: str, url: str):
        """Set up SiteStatus to monitor a website."""
        async with ctx.typing():
            async with self.config.guild(ctx.guild).sites() as sites:
                try:
                    async with aiohttp.ClientSession() as session:
                        start = time.perf_counter()
                        async with session.head(url) as response:
                            await ctx.maybe_send_embed(f"Site returned status `{response.status} {response.reason}` with latency `{round(time.perf_counter() - start, 1)}`s.")
                except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
                    return await ctx.send("There was an error connecting to this site. Is the url valid?")

                sites[sitename] = {
                    "url": url,
                    "status": 200,
                    "channel": None,
                    "online": None,
                    "offline": None,
                    "notify_channel": None,
                    "notify_role": None,
                    "last": None
                }
        return await ctx.tick()

    @_site_status.command(name="edit")
    async def _site_status_edit(self, ctx: commands.Context, sitename: str, url: str):
        """Edit the URL a SiteStatus monitored website."""
        async with ctx.typing():
            async with self.config.guild(ctx.guild).sites() as sites:
                if sitename not in sites.keys():
                    return await ctx.send("There was no monitored website found with that name!")

                try:
                    async with aiohttp.ClientSession() as session:
                        start = time.perf_counter()
                        async with session.head(url) as response:
                            await ctx.maybe_send_embed(f"Site returned status `{response.status} {response.reason}` with latency `{round(time.perf_counter() - start, 1)}`s.")
                except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
                    return await ctx.send("There was an error connecting to this site. Is the url valid?")

                sites[sitename]["url"] = url
        return await ctx.tick()

    @_site_status.command(name="remove", aliases=["delete"])
    async def _site_status_remove(self, ctx: commands.Context, sitename: str):
        """Remove a SiteStatus monitored website."""
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            del sites[sitename]
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_site_status.command(name="list")
    async def _site_status_list(self, ctx: commands.Context):
        """List the current SiteStatus monitored websites."""
        settings = await self.config.guild(ctx.guild).sites()
        embed = discord.Embed(title="Monitored SiteStatus Websites", color=await ctx.embed_color())
        if not settings:
            embed.description = "There are currently no monitored sites."
        else:
            for name, site in settings.items():
                embed.add_field(name=name, value=f"""
                **URL:** {site['url']}
                **Expected Status:** {site['status']}
                **Channel:** {self.bot.get_channel(site['channel']) if site['status'] else None}
                **Online Message:** {site['online']}
                **Offline Message:** {site['offline']}
                **Notify Channel:** {self.bot.get_channel(site['notify_channel']) if site['notify_channel'] else None}
                **Notify Role:** {ctx.guild.get_role(site['notify_role']) if site['notify_role'] else None}
                """)
        return await ctx.send(embed=embed)

    @_site_status.group(name="channel")
    async def _site_status_channel(self, ctx: commands.Context):
        """Display Status in Channels"""

    @_site_status_channel.command(name="set")
    async def _site_status_channel_set(self, ctx: commands.Context, sitename: str, channel: discord.VoiceChannel = None):
        """Set a voice channel to display a website's status (leave channel blank to remove)."""
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            sites[sitename]["channel"] = channel.id if channel else None
        return await ctx.tick()

    @_site_status_channel.command(name="online")
    async def _site_status_channel_online(self, ctx: commands.Context, sitename: str, *, template: str = None):
        """
        Set the channel name template for an "online" website status (leave blank to reset).

        The following are options you can include inside the template:
        `{status}` to display the HTTP status code received
        `{reason}` to display the meaning behind the HTTP status code
        `{latency}` to display the latency of the request (in the form of `x.x` seconds)
        """
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            sites[sitename]["online"] = template
        return await ctx.tick()

    @_site_status_channel.command(name="offline")
    async def _site_status_channel_offline(self, ctx: commands.Context, sitename: str, *, template: str = None):
        """
        Set the channel name template for an "offline" website status (leave blank to reset).

        The following are options you can include inside the template:
        `{status}` to display the HTTP status code received
        `{reason}` to display the meaning behind the HTTP status code
        `{latency}` to display the latency of the request (in the form of `x.x` seconds)
        """
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            sites[sitename]["offline"] = template
        return await ctx.tick()

    @_site_status.command(name="notify")
    async def _site_status_notify(self, ctx: commands.Context, sitename: str, role: discord.Role = None):
        """Notify a role in the current channel when a website is "offline" (leave empty to remove)."""
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            sites[sitename]["notify_channel"] = ctx.channel.id if role else None
            sites[sitename]["notify_role"] = role.id if role else None
        return await ctx.tick()

    @_site_status.command(name="expected")
    async def _site_status_expected(self, ctx: commands.Context, sitename: str, expected_status: int = 200):
        """Set the expected "online" HTTP status code of a monitored website (default is `200`)."""
        async with self.config.guild(ctx.guild).sites() as sites:
            if sitename not in sites.keys():
                return await ctx.send("There was no monitored website found with that name!")

            sites[sitename]["status"] = expected_status
        return await ctx.tick()

    @tasks.loop(minutes=5)
    async def _fetch_statuses(self):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            async with self.config.guild(self.bot.get_guild(guild)).sites() as sites:
                for name, site in sites.items():
                    if not(site["channel"] or site["notify_channel"] or site["notify_role"]):
                        continue
                    try:
                        async with aiohttp.ClientSession() as session:
                            start = time.perf_counter()
                            async with session.head(site['url']) as response:
                                latency = time.perf_counter() - start
                                code = (response.status, response.reason)
                    except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
                        latency = None
                        code = (500, "Internal Server Error")

                    # If monitoring channel set up, then update name if necessary
                    if site["channel"]:
                        channel = self.bot.get_channel(site["channel"])
                        if channel and channel.permissions_for(channel.guild.me).manage_channels:
                            online = site['online'] or "ONLINE"
                            offline = site['offline'] or "OFFLINE"

                            online_filled = await self._fill_template(online, code, latency)
                            offline_filled = await self._fill_template(offline, code, latency)

                            try:
                                if code[0] == site["status"]:
                                    if channel.name != online_filled:  # Edit if necessary
                                        await asyncio.wait_for(
                                            channel.edit(
                                                name=online_filled,
                                                reason="SiteStatus: site is online"
                                            ),
                                            timeout=5
                                        )
                                else:
                                    if channel.name != offline_filled:  # Edit if necessary
                                        await asyncio.wait_for(
                                            channel.edit(
                                                name=offline_filled,
                                                reason="SiteStatus: site is offline"
                                            ),
                                            timeout=5
                                        )
                            except asyncio.TimeoutError:
                                pass

                    # If notifications set up, then send message if necessary
                    if site["notify_channel"] and site["notify_role"]:
                        notify_channel = self.bot.get_channel(site["notify_channel"])
                        notify_role = self.bot.get_guild(guild).get_role(site["notify_role"])
                        if notify_channel and notify_role:
                            if code[0] != site["status"] and not site.get("last"):
                                await self._maybe_send_embed(
                                    channel=notify_channel,
                                    role=notify_role,
                                    site=(name, site['url']),
                                    message=f"is currently offline with status code `{code[0]} {code[1]}`!",
                                    color=discord.Color.red()
                                )
                            elif code[0] == site["status"] and site.get("last"):
                                downtime = round((time.time() - site.get("last")) / 60, 1)
                                await self._maybe_send_embed(
                                    channel=notify_channel,
                                    role=notify_role,
                                    site=(name, site['url']),
                                    message=f"is back online! It was down for roughly {downtime} minutes.",
                                    color=discord.Color.green()
                                )

                    # Set the "last" status
                    if not site.get("last"):
                        site["last"] = None if code[0] == site["status"] else time.time()
                    elif code[0] == site["status"]:
                        site["last"] = None

    @_fetch_statuses.before_loop
    async def _before_fetch_statuses(self):
        await self.bot.wait_until_red_ready()

    @staticmethod
    async def _fill_template(template, code, lat):
        return template.replace(
            "{status}", str(code[0])
        ).replace(
            "{reason}", code[1]
        ).replace(
            "{latency}", f"{round(lat, 1)}s" if isinstance(lat, float) else "N/A"
        )

    @staticmethod
    async def _maybe_send_embed(channel: discord.TextChannel, role: discord.Role, site: tuple, message: str, color: discord.Color):
        channel_permissions = channel.permissions_for(channel.guild.me)
        if not channel_permissions.send_messages or not (role.mentionable or channel.guild.me.guild_permissions.mention_everyone):
            return
        if channel_permissions.embed_links:
            await channel.send(
                f"{role.mention}",
                allowed_mentions=discord.AllowedMentions(roles=True),
                embed=discord.Embed(
                    title="SiteStatus Alert",
                    description=f"[{site[0]}]({site[1]}) {message}",
                    color=color,
                    timestamp=datetime.utcnow()
                )
            )
        else:
            await channel.send(
                f"{role.mention} <{site[1]}> {message}",
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

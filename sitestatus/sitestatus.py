from redbot.core import commands, Config
from discord.ext import tasks
import discord
import aiohttp
import asyncio
import time
from datetime import datetime


class SiteStatus(commands.Cog):
    """Display Website Statuses"""

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
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    return await ctx.send(f"Site returned status code `{response.status}`.")
        except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
            return await ctx.send("There was an error connecting to this site. Is the url valid?")

    @commands.guild_only()
    @commands.admin()
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
                        async with session.head(url) as response:
                            await ctx.send(f"Site returned status code `{response.status}`.")
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
                        async with session.head(url) as response:
                            await ctx.send(f"Site returned status code `{response.status}`.")
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

        If you would like to display the HTTP status code received, include `{status}` inside the template.
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

        If you would like to display the HTTP status code received, include `{status}` inside the template.
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
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            async with self.config.guild(self.bot.get_guild(guild)).sites() as sites:
                for name, site in sites.items():
                    if not(site["channel"] or site["notify_channel"] or site["notify_role"]):
                        continue
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.head(site['url']) as response:
                                code = response.status
                    except (aiohttp.InvalidURL, aiohttp.ClientConnectorError):
                        code = 500

                    # If monitoring channel set up, then update name if necessary
                    if site["channel"]:
                        channel = self.bot.get_channel(site["channel"])
                        if channel:
                            online = site['online'] or "ONLINE"
                            offline = site['offline'] or "OFFLINE"
                            try:
                                if code == site["status"]:
                                    if channel.name != online.replace("{status}", str(code)):  # Edit if necessary
                                        await asyncio.wait_for(
                                            channel.edit(
                                                name=online.replace("{status}", str(code)),
                                                reason="SiteStatus: site is online"
                                            ),
                                            timeout=5
                                        )
                                else:
                                    if channel.name != offline.replace("{status}", str(code)):  # Edit if necessary
                                        await asyncio.wait_for(
                                            channel.edit(
                                                name=offline.replace("{status}", str(code)),
                                                reason="SiteStatus: site is offline"
                                            ),
                                            timeout=5
                                        )
                            except (discord.Forbidden, discord.InvalidArgument, discord.HTTPException, asyncio.TimeoutError):
                                pass

                    # If notifications set up, then send message if necessary
                    if site["notify_channel"] and site["notify_role"]:
                        notify_channel = self.bot.get_channel(site["notify_channel"])
                        notify_role = self.bot.get_guild(guild).get_role(site["notify_role"])
                        if notify_channel and notify_role:
                            if code != site["status"] and not site.get("last"):
                                try:
                                    await notify_channel.send(
                                        f"{notify_role.mention}",
                                        allowed_mentions=discord.AllowedMentions(roles=True),
                                        embed=discord.Embed(
                                            title="SiteStatus Alert",
                                            description=f"[{name}]({site['url']}) is currently offline with status code `{code}`!",
                                            color=discord.Color.red(),
                                            timestamp=datetime.utcnow()
                                        )
                                    )
                                except discord.Forbidden:
                                    try:
                                        await notify_channel.send(
                                            f"{notify_role.mention} <{site['url']}> is currently offline with status code `{code}`!",
                                            allowed_mentions=discord.AllowedMentions(roles=True)
                                        )
                                    except (discord.Forbidden, discord.HTTPException):
                                        pass
                                except discord.HTTPException:
                                    pass
                            elif code == site["status"] and site.get("last"):
                                downtime = round((time.time() - site.get("last")) / 60, 1)
                                try:
                                    await notify_channel.send(
                                        f"{notify_role.mention}",
                                        allowed_mentions=discord.AllowedMentions(roles=True),
                                        embed=discord.Embed(
                                            title="SiteStatus Alert",
                                            description=f"[{name}]({site['url']}) is back online! It was down for roughly {downtime} minutes.",
                                            color=discord.Color.green(),
                                            timestamp=datetime.utcnow()
                                        )
                                    )
                                except discord.Forbidden:
                                    try:
                                        await notify_channel.send(f"<{site['url']}> is back online! It was down for roughly {downtime} minutes.")
                                    except (discord.Forbidden, discord.HTTPException):
                                        pass
                                except discord.HTTPException:
                                    pass

                    # Set the "last" status
                    if not site.get("last"):
                        site["last"] = None if code == site["status"] else time.time()
                    elif code == site["status"]:
                        site["last"] = None

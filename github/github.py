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
import time
import aiohttp
import feedparser
from dateutil import parser
from datetime import datetime

import discord
from discord.ext import tasks
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import escape


class GitHub(commands.Cog):
    """
    GitHub RSS Commit Feeds

    Sends GitHub commit messages exactly as the webhook would.
    """

    def __init__(self, bot):
        self.bot = bot
        self._github_rss.start()

        self.config = Config.get_conf(self, 14000605, force_registration=True)
        self.config.register_guild(feeds={}, channel=None, role=None, limit=5)

        self.color = 0x7289da
        self.githubURL = r"https://github.com/(.*?)/(.*?)/?"
        self.invalid = "Invalid GitHub URL. Try doing `[p]github whatlinks` to see the accepted formats."

    def cog_unload(self):
        self._github_rss.cancel()

    @staticmethod
    async def commit_embed(entry, gh_link):
        title_regex = r"https://github.com/.*?/(.*?)/commits/(.*)"
        title = re.fullmatch(title_regex, gh_link)
        title = f"[{title.group(1)}:{title.group(2)}] 1 new commit"

        desc_regex = r"https://github.com/.*?/.*?/commit/(.*)"
        desc = re.fullmatch(desc_regex, entry.link).group(1)[:7]
        desc = f"[`{desc}`]({entry.link}) {entry.title} – {entry.author}"
        t = parser.isoparse(entry.updated)
        t.replace(tzinfo=None)
        e = discord.Embed(title=title, color=0x7289da, description=desc, url=entry.link, timestamp=t)
        e.set_author(name=entry.author, url=entry.href, icon_url=entry.media_thumbnail[0]["url"])
        return e

    @staticmethod
    async def commit_embeds(entries, gh_link, url):
        title_regex = r"https://github.com/.*?/(.*?)/commits/(.*)"
        title = re.fullmatch(title_regex, gh_link)

        commits_regex = r"(https://github.com/.*?/.*?)/.*"
        commits_link = f"{re.fullmatch(commits_regex, url).group(1)}/commits"

        desc_regex = r"https://github.com/.*?/.*?/commit/(.*)"
        desc = ""
        num = 0
        for e in entries:
            if num >= 10: break
            desc0 = re.fullmatch(desc_regex, e.link).group(1)[:7]
            desc += f"[`{desc0}`]({e.link}) {e.title} – {e.author}\n"
            num += 1
        title = f"[{title.group(1)}:{title.group(2)}] {num} new commits"
        t = parser.isoparse(entries[0].updated).replace(tzinfo=None)
        e = discord.Embed(title=title, color=0x7289da, description=desc, url=commits_link, timestamp=t)

        e.set_author(name=entries[0].author, url=entries[0].href, icon_url=entries[0].media_thumbnail[0]["url"])
        return e

    @staticmethod
    async def new_entries(entries, last_time):
        new_time = datetime.utcnow()
        new_entries = []
        for e in entries:
            e_time = parser.isoparse(e.updated).replace(tzinfo=None)
            if e_time > last_time:
                new_entries.insert(0, e)
            else:
                break
        return new_entries, new_time

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(name="github")
    @commands.guild_only()
    async def _github(self, ctx: commands.Context):
        """GitHub RSS Feeds"""

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="setchannel")
    async def _set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the GitHub RSS feed channel."""
        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await ctx.send(f"I do not have the necessary permissions (send messages & embed links) in {channel.mention}!")

        await self.config.guild(ctx.guild).channel.set(channel.id)
        return await ctx.send(f"The GitHub RSS feed channel has been set to {channel.mention}.")

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="setrole")
    async def _set_role(self, ctx: commands.Context, role: discord.Role = None):
        """Set the GitHub RSS feed role."""
        if role is None:
            await self.config.guild(ctx.guild).role.set(None)
            return await ctx.send(f"The GitHub RSS feed role requirement has been removed.")
        else:
            await self.config.guild(ctx.guild).role.set(role.id)
            return await ctx.send(f"The GitHub RSS feed role has been set to {role.mention}.")

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="setlimit")
    async def _set_limit(self, ctx: commands.Context, num: int = 5):
        """Set the GitHub RSS feed limit per user."""
        await self.config.guild(ctx.guild).limit.set(num)
        return await ctx.send(f"The GitHub RSS feed limit per user has been set to {num}.")

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="get")
    async def _get(self, ctx: commands.Context, url: str, private=False):
        """Test out a GitHub url."""
        if not private:
            match = re.fullmatch(self.githubURL, url)
            if match is None:
                return await ctx.send(self.invalid)

            url = f"https://github.com/{match.group(1)}/{match.group(2)}/commits.atom"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.read()
                if resp.status != 200:
                    return await ctx.send(self.invalid)
        entry = feedparser.parse(html).entries[0]
        e = await self.commit_embed(entry, feedparser.parse(html).feed.link)
        await ctx.send(embed=e)

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="force")
    async def _force(self, ctx: commands.Context, user: discord.Member, name: str):
        """Force a specific RSS feed to post."""
        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                url = feeds[str(user.id)][name]["url"]
            except KeyError:
                return await ctx.send("No feed found.")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.read()
                if resp.status != 200:
                    return await ctx.send(self.invalid)
        entry = feedparser.parse(html).entries[0]
        e = await self.commit_embed(entry, feedparser.parse(html).feed.link)

        ch = self.bot.get_channel(await self.config.guild(ctx.guild).channel())
        return await ch.send(embed=e)

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="forceall")
    async def _force_all(self, ctx: commands.context):
        """Force a run of the RSS feed fetching coro."""
        async with ctx.typing():
            await self._github_rss.coro(self, guild_to_check=ctx.guild.id)
        return await ctx.tick()

    @_github.command(name="whatlinks")
    async def _what_links(self, ctx: commands.Context):
        """What links can you submit to `[p]github add`?"""
        color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(title=f"What links can you submit to `{ctx.clean_prefix}github add`?", color=color)
        e.add_field(name="Public Repos", inline=False, value=f"Just enter your **repo link**! For example, `{ctx.clean_prefix}github add SomeName https://github.com/github/testrepo`. Any other link (e.g. your `.git` link) will not work.")
        e.add_field(name="Private Repos", inline=False, value=f"Inspect element, search in your **repo** html for `.atom`, copy that entire link (with the `?token=sometoken`), do `{ctx.clean_prefix}github add SomeName ThatLinkYouJustCopied true`. Be sure to include `true` at the end to signal that this is a private repo.")
        return await ctx.send(embed=e)

    @_github.command(name="add")
    async def _add(self, ctx: commands.Context, name: str, url: str, private=False):
        """
        Add a GitHub RSS feed to the server.

        For the accepted link formats, see `[p]github whatlinks`.
        """

        role = await self.config.guild(ctx.guild).role()
        if role is not None:
            if role not in [r.id for r in ctx.author.roles]:
                return await ctx.send("You do not have the required role!")

        if len(name) > 20: return await ctx.send("That feed name is too long!")
        name = escape(name)

        ch = await self.config.guild(ctx.guild).channel()

        if ch is None:
            return await ctx.send("The mods have not set up a GitHub RSS feed channel yet.")

        if not private:
            match = re.fullmatch(self.githubURL, url)
            if match is None:
                return await ctx.send(self.invalid)

            url = f"https://github.com/{match.group(1)}/{match.group(2)}/commits.atom"
        else:
            if not(url.startswith("https://github.com/")): return await ctx.send("That is not a GitHub link!")
            private_repo = r"https://github.com/(.*?)/(.*?)/.*?\.atom\?token=.*?"
            match = re.fullmatch(private_repo, url)
            if match is None: return await ctx.send(f"Your token was missing! Follow the instructions in `{ctx.clean_prefix}github whatlinks`.")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.read()
                if resp.status not in [200, 304]:
                    return await ctx.send(self.invalid)

        guild_limit = await self.config.guild(ctx.guild).limit()
        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                if name in feeds[str(ctx.author.id)]:
                    return await ctx.send("There is already a feed with that name!")
                elif url in [n[1]["url"] for n in feeds[str(ctx.author.id)].items()]:
                    return await ctx.send("There is already a feed with that link!")
                elif len(feeds[str(ctx.author.id)].items()) > guild_limit:
                    return await ctx.send(f"You already have {guild_limit} feeds in this server!")
                feeds[str(ctx.author.id)][name] = {"url": url, "time": datetime.utcnow().timestamp()}
            except KeyError:
                feeds[str(ctx.author.id)] = {name: {"url": url, "time": datetime.utcnow().timestamp()}}

        ch = self.bot.get_channel(ch)
        name_regex = r"https://github.com/.*?/(.*?)/commits/(.*)"
        name = re.fullmatch(name_regex, feedparser.parse(html).feed.link)
        entry = feedparser.parse(html).entries[0]

        repo_regex = r"(https://github.com/.*?/.*?)/.*"
        await ch.send(embed=discord.Embed(
            color=discord.Color.green(),
            description=f"[[{name.group(1)}:{name.group(2)}]]({re.fullmatch(repo_regex, url).group(1)}) has been added by {ctx.author.mention}"
        ))

        await ch.send(embed=await self.commit_embed(entry, feedparser.parse(html).feed.link))

        return await ctx.send("Feed successfully added.")

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="rename")
    async def _rename(self, ctx: commands.Context, user: discord.Member, old_name: str, new_name: str):
        """Rename a feed."""

        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                feeds[str(user.id)][new_name] = feeds[str(user.id)].pop(old_name)
            except KeyError:
                return await ctx.send("Feed not found.")

        return await ctx.send("Feed successfully renamed.")

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="channel")
    async def _channel(self, ctx: commands.Context, user: discord.Member, feed_name: str, channel: discord.TextChannel = None):
        """Set a channel override for a feed (leave empty to reset)."""

        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await ctx.send(f"I do not have the necessary permissions (send messages & embed links) in {channel.mention}!")

        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                if channel:
                    feeds[str(user.id)][feed_name]["channel"] = channel.id
                else:
                    del feeds[str(user.id)][feed_name]["channel"]
            except KeyError:
                return await ctx.send("Feed not found.")

        return await ctx.send("Feed channel successfully overridden.")

    @_github.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, name: str):
        """Remove a GitHub RSS feed from the server."""
        role = await self.config.guild(ctx.guild).role()
        if role is not None:
            if role not in [r.id for r in ctx.author.roles]:
                return await ctx.send("You do not have the required role!")

        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                if name not in feeds[str(ctx.author.id)]:
                    return await ctx.send(f"There is no feed with that name! Try checking your feeds with `{ctx.clean_prefix}github list`.")

                url = feeds[str(ctx.author.id)][name]["url"]
                repo_regex = r"(https://github.com/.*?/.*?)/.*"
                e0 = discord.Embed(color=discord.Color.red(), description=f"[{name}]({re.fullmatch(repo_regex, url).group(1)}) has been removed by {ctx.author.mention}")
                await self.bot.get_channel(await self.config.guild(ctx.guild).channel()).send(embed=e0)

                del feeds[str(ctx.author.id)][name]
            except KeyError:
                return await ctx.send(f"There is no feed with that name! Try checking your feeds with `{ctx.clean_prefix}github list`.")

        return await ctx.send("Feed successfully removed.")

    @_github.command(name="list")
    async def _list(self, ctx: commands.Context):
        """List your GitHub RSS feeds in the server."""
        color = await self.bot.get_embed_color(ctx)

        role = await self.config.guild(ctx.guild).role()
        if role is not None:
            if role not in [r.id for r in ctx.author.roles]:
                return await ctx.send("You do not have the required role!")

        feeds_string = ""
        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                repo_regex = r"(https://github.com/.*?/.*?)/.*"
                for name, feed in feeds[str(ctx.author.id)].items():
                    feeds_string += f"`{name}`: <{re.fullmatch(repo_regex, feed['url']).group(1)}>\n"
            except KeyError:
                return await ctx.send("No feeds found.")
        if feeds_string == "": return await ctx.send(f"No feeds found. Try adding one with `{ctx.clean_prefix}github add`!")
        return await ctx.send(embed=discord.Embed(title="Your GitHub RSS Feeds", description=feeds_string, color=color))

    @commands.admin_or_permissions(administrator=True)
    @_github.command(name="listall")
    async def _list_all(self, ctx: commands.Context):
        """List all GitHub RSS feeds in the server."""
        color = await self.bot.get_embed_color(ctx)

        feeds_string = ""
        async with ctx.typing():
            async with self.config.guild(ctx.guild).feeds() as feeds:
                repo_regex = r"(https://github.com/.*?/.*?)/.*"
                for id, fs in feeds.items():
                    feeds_string += f"{(await self.bot.get_or_fetch_user(int(id))).mention}: `{len(fs)}` feed(s) \n"
                    for n, f in fs.items():
                        feeds_string += f"- `{n}`: <{re.fullmatch(repo_regex, f['url']).group(1)}>\n"

        return await ctx.send(embed=discord.Embed(title="Server GitHub RSS Feeds", description=feeds_string, color=color))

    @tasks.loop(minutes=3)
    async def _github_rss(self, guild_to_check=None):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            if guild_to_check and guild != guild_to_check:
                continue

            g = self.bot.get_guild(guild)
            ch = self.bot.get_channel(await self.config.guild(g).channel())

            if not ch.permissions_for(g.me).embed_links:
                continue

            async with self.config.guild(g).feeds() as feeds:
                for u, fs0 in feeds.items():
                    for n, fs in fs0.items():
                        if not (url := fs.get("url")):
                            continue

                        # Fetch feed
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url) as resp:
                                html = await resp.read()
                                if resp.status != 200:
                                    continue

                        # Parse feed
                        entries = feedparser.parse(html).entries
                        new_entries, new_time = await self.new_entries(entries, datetime.fromtimestamp(float(fs["time"])))

                        # Create embeds
                        e = None
                        if len(new_entries) == 1:
                            e = await self.commit_embed(new_entries[0], feedparser.parse(html).feed.link)
                        elif len(new_entries) > 1:
                            e = await self.commit_embeds(new_entries, feedparser.parse(html).feed.link, fs["url"])

                        # Send embeds
                        if e:
                            if fs.get("channel"):
                                c = self.bot.get_channel(fs["channel"])
                                if c.permissions_for(g.me).embed_links:
                                    await c.send(embed=e)
                            else:
                                await ch.send(embed=e)
                        fs["time"] = new_time.timestamp()

    @_github_rss.before_loop
    async def _before_github_rss(self):
        await self.bot.wait_until_red_ready()

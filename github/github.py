import aiohttp
import datetime
import discord
import feedparser
import re
import time

from discord.ext import tasks
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import escape


class Github(commands.Cog):
    """
    Github RSS Commit Feeds

    Sends Github commit messages exactly as the webhook would.
    """

    def __init__(self, bot):
        self.bot = bot
        self.github_rss.start()

        self.config = Config.get_conf(self, 14000605, force_registration=True)
        self.config.register_guild(feeds={}, channel=None, role=None, limit=5)

        self.color = 0x7289da
        self.githubURL = r"https://github.com/(.*?)/(.*?)/?"
        self.invalid = "Invalid Github URL. Try doing `[p]github whatlinks` to see the accepted formats."

    def cog_unload(self):
        self.github_rss.cancel()

    @staticmethod
    async def commit_embed(entry, gh_link):
        title_regex = r"https://github.com/.*?/(.*?)/commits/(.*)"
        title = re.fullmatch(title_regex, gh_link)
        title = f"[{title.group(1)}:{title.group(2)}] 1 new commit"

        desc_regex = r"https://github.com/.*?/.*?/commit/(.*)"
        desc = re.fullmatch(desc_regex, entry.link).group(1)[:7]
        desc = f"[`{desc}`]({entry.link}) {entry.title} – {entry.author}"
        t = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
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
        t = datetime.datetime.fromtimestamp(time.mktime(entries[0].updated_parsed))
        e = discord.Embed(title=title, color=0x7289da, description=desc, url=commits_link, timestamp=t)

        e.set_author(name=entries[0].author, url=entries[0].href, icon_url=entries[0].media_thumbnail[0]["url"])
        return e

    @staticmethod
    async def new_entries(entries, last_time):
        new_time = time.time()
        new_entries = []
        for e in entries:
            e_time = time.mktime(e.updated_parsed)
            if e_time > last_time:
                new_entries.insert(0, e)
            else:
                break
        return new_entries, new_time

    @commands.group()
    @commands.guild_only()
    async def github(self, ctx: commands.Context):
        """Github RSS Feeds"""

    @commands.admin()
    @github.command()
    async def setchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the Github RSS feed channel."""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        return await ctx.send(f"The Github RSS feed channel has been set to {channel.mention}.")

    @commands.admin()
    @github.command()
    async def setrole(self, ctx: commands.Context, role: discord.Role = None):
        """Set the Github RSS feed role."""
        if role is None:
            await self.config.guild(ctx.guild).role.set(None)
            return await ctx.send(f"The Github RSS feed role requirement has been removed.")
        else:
            await self.config.guild(ctx.guild).role.set(role.id)
            return await ctx.send(f"The Github RSS feed role has been set to {role.mention}.")

    @commands.admin()
    @github.command()
    async def setlimit(self, ctx: commands.Context, num: int = 5):
        """Set the Github RSS feed limit per user."""
        await self.config.guild(ctx.guild).limit.set(num)
        return await ctx.send(f"The Github RSS feed limit per user has been set to {num}.")

    @commands.admin()
    @github.command()
    async def get(self, ctx: commands.Context, url: str, private=False):
        """Test out a Github url."""
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

    @commands.admin()
    @github.command()
    async def force(self, ctx: commands.Context, user: discord.Member, name: str):
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

    @commands.admin()
    @github.command()
    async def forceall(self, ctx: commands.context):
        """Force a run of the RSS feed fetching coro."""
        await self.github_rss.coro(self)
        return await ctx.tick()

    @github.command()
    async def whatlinks(self, ctx: commands.Context):
        """What links can you submit to `[p]github add`?"""
        color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(title=f"What links can you submit to `{ctx.clean_prefix}github add`?", color=color)
        e.add_field(name="Public Repos", inline=False, value=f"Just enter your **repo link**! For example, `{ctx.clean_prefix}github add SomeName https://github.com/github/testrepo`. Any other link (e.g. your `.git` link) will not work.")
        e.add_field(name="Private Repos", inline=False, value=f"Inspect element, search in your **repo** html for `.atom`, copy that entire link (with the `?token=sometoken`), do `{ctx.clean_prefix}github add SomeName ThatLinkYouJustCopied true`. Be sure to include `true` at the end to signal that this is a private repo.")
        return await ctx.send(embed=e)

    @github.command()
    async def add(self, ctx: commands.Context, name: str, url: str, private=False):
        """
        Add a Github RSS feed to the server.

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
            return await ctx.send("The mods have not set up a Github RSS feed channel yet.")

        if not private:
            match = re.fullmatch(self.githubURL, url)
            if match is None:
                return await ctx.send(self.invalid)

            url = f"https://github.com/{match.group(1)}/{match.group(2)}/commits.atom"
        else:
            if not(url.startswith("https://github.com/")): return await ctx.send("That is not a Github link!")
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
                feeds[str(ctx.author.id)][name] = {"url": url, "time": time.time()}
            except KeyError:
                feeds[str(ctx.author.id)] = {name: {"url": url, "time": time.time()}}

        ch = self.bot.get_channel(ch)
        name_regex = r"https://github.com/.*?/(.*?)/commits/(.*)"
        name = re.fullmatch(name_regex, feedparser.parse(html).feed.link)
        entry = feedparser.parse(html).entries[0]

        repo_regex = r"(https://github.com/.*?/.*?)/.*"
        e0 = discord.Embed(color=discord.Color.green(), description=f"[[{name.group(1)}:{name.group(2)}]]({re.fullmatch(repo_regex, url).group(1)}) has been added by {ctx.author.mention}")
        await ch.send(embed=e0)

        e1 = await self.commit_embed(entry, feedparser.parse(html).feed.link)
        await ch.send(embed=e1)

        return await ctx.send("Feed successfully added.")

    @commands.admin()
    @github.command()
    async def rename(self, ctx: commands.Context, user: discord.Member, old_name: str, new_name: str):
        """Rename a feed."""

        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                feeds[str(user.id)][new_name] = feeds[str(user.id)].pop(old_name)
            except KeyError:
                return await ctx.send("Feed not found.")

        return await ctx.send("Feed successfully renamed.")

    @commands.admin()
    @github.command()
    async def channel(self, ctx: commands.Context, user: discord.Member, feed_name: str, channel: discord.TextChannel = None):
        """Set a channel override for a feed (leave empty to reset)."""

        async with self.config.guild(ctx.guild).feeds() as feeds:
            try:
                if channel:
                    feeds[str(user.id)][feed_name]["channel"] = channel.id
                else:
                    del feeds[str(user.id)][feed_name]["channel"]
            except KeyError:
                return await ctx.send("Feed not found.")

        return await ctx.send("Feed channel successfully overridden.")

    @github.command()
    async def remove(self, ctx: commands.Context, name: str):
        """Remove a Github RSS feed from the server."""
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

    @github.command()
    async def list(self, ctx: commands.Context):
        """List your Github RSS feeds in the server."""
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
        return await ctx.send(embed=discord.Embed(title="Your Github RSS Feeds", description=feeds_string, color=color))

    @commands.admin()
    @github.command()
    async def listall(self, ctx: commands.Context):
        """List all Github RSS feeds in the server."""
        color = await self.bot.get_embed_color(ctx)

        feeds_string = ""
        async with ctx.typing():
            async with self.config.guild(ctx.guild).feeds() as feeds:
                repo_regex = r"(https://github.com/.*?/.*?)/.*"
                for id, fs in feeds.items():
                    feeds_string += f"{(await self.bot.get_or_fetch_user(int(id))).mention}: `{len(fs)}` feed(s) \n"
                    for n, f in fs.items():
                        feeds_string += f"- `{n}`: <{re.fullmatch(repo_regex, f['url']).group(1)}>\n"

        return await ctx.send(embed=discord.Embed(title="Server Github RSS Feeds", description=feeds_string, color=color))

    @tasks.loop(minutes=3)
    async def github_rss(self):
        # start = time.time()
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            g = self.bot.get_guild(guild)
            ch = self.bot.get_channel(await self.config.guild(g).channel())
            async with self.config.guild(g).feeds() as feeds:
                for u, fs0 in feeds.items():
                    for n, fs in fs0.items():
                        try:
                            url = fs["url"]
                        except KeyError:
                            continue

                        async with aiohttp.ClientSession() as session:
                            async with session.get(url) as resp:
                                html = await resp.read()
                                if resp.status != 200:
                                    print(f"Invalid Github URL: {url}")

                        entries = feedparser.parse(html).entries
                        new_entries, new_time = await self.new_entries(entries, float(fs["time"]))
                        if len(new_entries) == 1:
                            e = await self.commit_embed(new_entries[0], feedparser.parse(html).feed.link)
                            if fs.get("channel"):
                                await self.bot.get_channel(fs["channel"]).send(embed=e)
                            else:
                                await ch.send(embed=e)
                        elif len(new_entries) > 1:
                            e = await self.commit_embeds(new_entries, feedparser.parse(html).feed.link, fs["url"])
                            if fs.get("channel"):
                                await self.bot.get_channel(fs["channel"]).send(embed=e)
                            else:
                                await ch.send(embed=e)
                        fs["time"] = new_time
        # print(f"This loop took {round(int(time.time() - start) / 60, 2)} minutes.")

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

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list, humanize_timedelta


class LFG(commands.Cog):
    """
    VC LFG System w/ Custom Fields

    An LFG cog with customizable fields, VC renaming, and invitations.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "message": "",
            "rename": True,
            "vc_name": [],
            "categories": {},
            "mention_limit": 3,
            "active": {}
        }
        self.config.register_guild(**default_guild)

        self.lfg_vc_bucket = commands.CooldownMapping.from_cooldown(
            1, 600, lambda channel: channel.id
        )

    @commands.Cog.listener("on_voice_state_update")
    async def _voice_listener(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        to_rename = await self.config.guild(member.guild).rename()

        if before.channel and (not after.channel or before.channel.id != after.channel.id) and not before.channel.members:
            async with self.config.guild(member.guild).active() as active:
                if original_name := active.get(str(before.channel.id)):
                    del active[str(before.channel.id)]
                    if before.channel.permissions_for(member.guild.me).manage_channels and before.channel.name != original_name:
                        if to_rename:
                            await before.channel.edit(name=original_name, reason="LFG: all users left VC")

    @commands.guild_only()
    @commands.command(name="lfg", require_var_positional=True)
    async def _lfg(self, ctx: commands.Context, *inputs: str):
        """Looking for group."""
        if not ctx.author.voice or not (user_vc := ctx.author.voice.channel):
            return await ctx.send("You must be in a voice channel to use this command!")

        if not user_vc.permissions_for(ctx.guild.me).create_instant_invite:
            return await ctx.send("I cannot create invites!")

        if not user_vc.permissions_for(ctx.guild.me).manage_channels:
            return await ctx.send("I do not have permission to manage the VC!")

        # Thanks PCX for the cooldown bucket example
        retry = self.lfg_vc_bucket.get_bucket(user_vc).update_rate_limit()
        if retry:
            return await ctx.send(f"Due to Discord ratelimits, you can only run this command once every 10 minutes for the same VC. Please try again in {humanize_timedelta(seconds=max(retry, 1))}.")

        invite: discord.Invite = await user_vc.create_invite()
        settings: dict = await self.config.guild(ctx.guild).all()

        to_rename = []
        categories = {}
        for c, v in settings["categories"].items():
            v_lowered = [s.lower() for s in v]
            if not categories.get(c):
                for word in inputs:
                    if str(word).lower() in v_lowered:
                        categories[c] = v[v_lowered.index(str(word).lower())]
        for cat in settings["vc_name"]:
            if v := categories.get(cat):
                to_rename.append(v)
        to_rename = user_vc.name + " " + " | ".join(to_rename)

        users = [ctx.author.mention]
        count = 0
        while len(users) < settings["mention_limit"] and count < len(user_vc.members):
            if (u := user_vc.members[count]) != ctx.author:
                users.append(u.mention)
            count += 1

        to_send = settings["message"].replace(
            "{inputs}", " ".join(inputs)
        ).replace(
            "{invite}", invite.url
        ).replace(
            "{users}", humanize_list(users)
        ).replace(
            "{vcname}", to_rename
        )

        if not to_send or not to_rename:
            return await ctx.send("Please wait for an admin to setup the necessary settings first!")

        async with self.config.guild(ctx.guild).active() as active:
            if active.get(str(user_vc.id)):
                return await ctx.send("There is already an active LFG session in your VC!")
            active[str(user_vc.id)] = user_vc.name

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.message.delete()
        await ctx.send(to_send)
        return await user_vc.edit(name=to_rename, reason=f"LFG: {ctx.author} started a session")

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="lfgset")
    async def _lfg_set(self, ctx: commands.Context):
        """LFG Settings"""

    @_lfg_set.command(name="vcname")
    async def _vc_name(self, ctx: commands.Context, *categories: str):
        """Set the order of categories for VC renaming."""
        await self.config.guild(ctx.guild).vc_name.set(categories)
        return await ctx.tick()

    @_lfg_set.command(name="post", require_var_positional=True)
    async def _post(self, ctx: commands.Context, *, template: str):
        """
        Set the LFG post message (see below for replaceable options).

        `{inputs}`: the user's command inputs
        `{invite}`: the VC invite
        `{users}`: mentions of users in the VC
        `{vcname}`: the name of the VC
        """
        await self.config.guild(ctx.guild).message.set(template)
        return await ctx.tick()

    @_lfg_set.command(name="mentionlimit")
    async def _mention_limit(self, ctx: commands.Context, limit: int):
        """Set the maximum amount of users to mention in the invite message."""
        if limit < 1:
            return await ctx.send("Please enter a positive integer!")
        await self.config.guild(ctx.guild).mention_limit.set(limit)
        return await ctx.tick()

    @_lfg_set.command(name="rename")
    async def _rename(self, ctx: commands.Context, true_or_false: bool):
        """Set whether to rename the VC to its original state once empty."""
        await self.config.guild(ctx.guild).rename.set(true_or_false)
        return await ctx.tick()

    @_lfg_set.group(name="categories", invoke_without_command=True)
    async def _categories(self, ctx: commands.Context):
        """View and set the LFG categories and accepted values."""
        settings = await self.config.guild(ctx.guild).categories()
        description = ""
        for c, v in settings.items():
            description += f"**{c}:** {', '.join(v)}\n"
        await ctx.send(embed=discord.Embed(
            title="LFG Categories",
            description=description or "Not set.",
            color=await ctx.embed_color()
        ))
        await ctx.send_help()

    @_categories.command("set", require_var_positional=True)
    async def _categories_set(self, ctx: commands.Context, category: str, *values: str):
        """Set an LFG category and its accepted values."""
        async with self.config.guild(ctx.guild).categories() as settings:
            settings[category] = values
        return await ctx.tick()

    @_categories.command("remove", aliases=["delete"])
    async def _categories_remove(self, ctx: commands.Context, category: str):
        """Remove an LFG category."""
        async with self.config.guild(ctx.guild).categories() as settings:
            if category not in settings.keys():
                return await ctx.send(f"`{category}` is not a recognized LFG category!")
            del settings[category]
        return await ctx.tick()

    @_lfg_set.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the LFG settings."""
        settings = await self.config.guild(ctx.guild).all()
        return await ctx.send(embed=discord.Embed(
            title="LFG Settings",
            description=f"**Post:** {settings['message'] or None}\n**VC Name:** {', '.join(settings['vc_name']) or None}\n**Rename on Empty:** {settings['rename']}\n**Mention Limit:** {settings['mention_limit']}\n**Categories:** see `{ctx.clean_prefix}lfgset categories`",
            color=await ctx.embed_color()
        ))

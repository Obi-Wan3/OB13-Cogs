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

from datetime import datetime, timedelta

import discord
from redbot.core import commands, Config, bank
from redbot.core.utils import AsyncIter


class Referrals(commands.Cog):
    """
    Invite Referral -> Credits

    Allows users who refer others to the server to gain credits.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": False,
            "amount": 0,
            "time_limit": None,
            "already_redeemed": [],
            "log_channel": None,
            "account_age": None
        }
        self.config.register_guild(**default_guild)

    @commands.guild_only()
    @commands.command(name="referredby")
    async def _referredby(self, ctx: commands.Context, member: discord.Member):
        """Were you referred by another member of this server? Use this command to let them gain credits!"""

        # Referrals toggled off
        if not await self.config.guild(ctx.guild).toggle():
            return

        log_channel = await self.config.guild(ctx.guild).log_channel()
        if log_channel:
            log_channel = ctx.guild.get_channel(log_channel)
            if not (log_channel and log_channel.permissions_for(ctx.guild.me).send_messages):
                log_channel = None

        # User already ran command
        if ctx.author.id in await self.config.guild(ctx.guild).already_redeemed():
            if log_channel:
                await log_channel.send(f"{ctx.author.mention} tried to run `{ctx.clean_prefix}referredby` but has already done so before.")
            return await ctx.send("You have already ran this command! You can only use this once.")

        # Self-referral
        if ctx.author == member:
            if log_channel:
                await log_channel.send(f"{ctx.author.mention} tried to run `{ctx.clean_prefix}referredby` with a self-referral.")
            return await ctx.send("You cannot refer yourself!")

        # No credit set by admin yet
        to_deposit = await self.config.guild(ctx.guild).amount()
        if not credits:
            return await ctx.send("The admin have not set a credit amount to be given yet!")

        # Check if user is within time limit
        time_limit = await self.config.guild(ctx.guild).time_limit()
        if time_limit and not (
                ctx.author.joined_at and
                (ctx.author.joined_at > (datetime.now() - timedelta(hours=time_limit)))
        ):
            if log_channel:
                await log_channel.send(f"{ctx.author.mention} tried to run `{ctx.clean_prefix}referredby` but has exceeded the time limit.")
            return await ctx.send("Unfortunately, you have exceeded the time given to run this command after you join.")

        # Check if user account is older than the minimum age
        account_age = await self.config.guild(ctx.guild).account_age()
        if account_age and not (ctx.author.created_at < (datetime.now() - timedelta(hours=time_limit))):
            if log_channel:
                await log_channel.send(f"{ctx.author.mention} tried to run `{ctx.clean_prefix}referredby` but their account is too new.")
            return await ctx.send("Your account is too new!")

        new = await bank.deposit_credits(member, to_deposit)
        cname = await bank.get_currency_name(ctx.guild)

        async with self.config.guild(ctx.guild).already_redeemed() as already_redeemed:
            already_redeemed.append(ctx.author.id)

        # Log into channel if log_channel set
        if log_channel:
            await log_channel.send(f"{member.mention} has gained {to_deposit} {cname} for referring {ctx.author.mention}.")

        return await ctx.send(f"{member.mention} Thanks for referring another user! {to_deposit} {cname} have been deposited to your account. Your new balance is {new} {cname}.")

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="referset")
    async def _referset(self, ctx: commands.Context):
        """Settiings for Referrals"""

    @_referset.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle Referrals in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_referset.command(name="amount", aliases=["credits"])
    async def _amount(self, ctx: commands.Context, amount: int):
        """Set the amount given to those that refer others."""

        if not amount or amount < 1:
            return await ctx.send("Please enter a positive integer!")

        await self.config.guild(ctx.guild).amount.set(amount)
        return await ctx.tick()

    @_referset.command(name="timelimit")
    async def _time_limit(self, ctx: commands.Context, hours: int):
        """Set the time given to new users to run [p]referredby."""

        if not hours or hours < 1:
            return await ctx.send("Please enter a positive integer!")

        await self.config.guild(ctx.guild).time_limit.set(hours)
        return await ctx.tick()

    @_referset.command(name="accountage")
    async def _account_age(self, ctx: commands.Context, hours: int = None):
        """Set minimum account age for users to run [p]referredby (leave blank for none)."""

        if hours is None:
            await self.config.guild(ctx.guild).account_age.set(None)
        elif hours < 1:
            return await ctx.send("Please enter a positive integer!")
        else:
            await self.config.guild(ctx.guild).account_age.set(hours)
        return await ctx.tick()

    @_referset.command(name="logchannel")
    async def _log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel for logs to go into (leave blank for none)."""
        if channel:
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(f"I cannot send messages to {channel.mention}!")
            await self.config.guild(ctx.guild).log_channel.set(channel.id)
        else:
            await self.config.guild(ctx.guild).log_channel.set(None)
        return await ctx.tick()

    @_referset.command(name="initialize")
    async def _initialize(self, ctx: commands.Context, enter_true_to_confirm: bool):
        """Adds current members to the already-redeemed list (except those that joined within time limit)."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with ctx.typing():
            time_limit = await self.config.guild(ctx.guild).time_limit()

            if not time_limit:
                return await ctx.send(f"Please set the time limit first using `{ctx.clean_prefix}referset timelimit`!")

            async with self.config.guild(ctx.guild).already_redeemed() as already_redeemed:
                async for m in AsyncIter(ctx.guild.members, steps=500):
                    if (
                        m.joined_at and
                        (m.joined_at < (datetime.now() - timedelta(hours=time_limit))) and
                        m.id not in already_redeemed
                    ):
                        already_redeemed.append(m.id)

        return await ctx.send("The already-redeemed list was updated successfully!")

    @_referset.command(name="alreadyreferred")
    async def _already_referred(self, ctx: commands.Context, member: discord.Member):
        """Check if the user is has already used [p]referredby."""
        already_redeemed_list = await self.config.guild(ctx.guild).already_redeemed()
        if member.id in already_redeemed_list:
            return await ctx.send(f"This member has already used `{ctx.clean_prefix}referredby`.")
        else:
            return await ctx.send(f"This member has not yet used `{ctx.clean_prefix}referredby`.")

    @_referset.command(name="resetall")
    async def _resetall(self, ctx: commands.Context, enter_true_to_confirm: bool):
        """Reset all Referrals settings."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        await self.config.guild(ctx.guild).clear()
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_referset.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View current Referrals settings."""

        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(
            title="Referrals Settings",
            color=await ctx.embed_color(),
            description=f"""
            **Toggle:** {settings['toggle']}
            **Amount:** {settings['amount']} {await bank.get_currency_name(ctx.guild)}
            **Log Channel:** {ctx.guild.get_channel(settings['log_channel']).mention if settings['log_channel'] and ctx.guild.get_channel(settings['log_channel']) else "None"}
            **Min. Account Age:** {str(settings['account_age'])+' hours' if settings['account_age'] else None}
            **Time Limit:** {f"{settings['time_limit']} hours within join" if settings['time_limit'] else "Not Set"}
            """
        )
        return await ctx.send(embed=embed)

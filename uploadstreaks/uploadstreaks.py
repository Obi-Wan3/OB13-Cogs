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

import typing
from datetime import datetime, timedelta, timezone

import discord
from redbot.core import commands, Config, bank
from redbot.core.utils.chat_formatting import humanize_list


class UploadStreaks(commands.Cog):
    """
    Streaks & Points for Uploads

    A leaderboard with points and streaks for uploading attachments in specific channels per interval of time.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "challenges": {}
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):

        # Ignore these messages
        if (
                not message.guild or  # Message not in a guild
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                message.author.bot or  # Message author is a bot
                not message.attachments  # There are no attachments in this message
        ):
            return

        async with self.config.guild(message.guild).challenges() as settings:
            for challenge in settings.values():
                if (
                        not challenge['active'] or  # Challenge not active
                        message.channel.id not in challenge['channels'] or  # Message not in challenge channel
                        (challenge['role'] and challenge['role'] not in [r.id for r in message.author.roles]) or  # Author does not have role
                        datetime.utcfromtimestamp(challenge['interval'][1]) > datetime.utcnow()  # Challenge not started
                ):
                    continue

                orig = challenge['users'].get(str(message.author.id))
                if orig:
                    interval_before = (datetime.utcnow() - timedelta(days=challenge['interval'][0])).replace(microsecond=0, second=0, minute=0, hour=challenge['interval'][2], tzinfo=timezone.utc).timestamp()
                    interval_start = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=challenge['interval'][2], tzinfo=timezone.utc).timestamp()
                    interval_end = (datetime.utcnow() + timedelta(days=challenge['interval'][0])).replace(microsecond=0, second=0, minute=0, hour=challenge['interval'][2], tzinfo=timezone.utc).timestamp()

                    # Last entry was also in this interval
                    if interval_start <= challenge['users'][str(message.author.id)][2] <= interval_end:
                        challenge['users'][str(message.author.id)] = (orig[0], orig[1], message.created_at.timestamp())
                        continue

                    # Streak continued
                    if interval_before <= challenge['users'][str(message.author.id)][2] <= interval_start:
                        challenge['users'][str(message.author.id)] = (orig[0]+1, orig[1]+1, message.created_at.timestamp())

                    # Streak restarted
                    else:
                        challenge['users'][str(message.author.id)] = (orig[0]+1, 1, message.created_at.timestamp())

                else:
                    challenge['users'][str(message.author.id)] = (1, 1, message.created_at.timestamp())

                if challenge['credits'] > 0:
                    await bank.deposit_credits(message.author, challenge['credits'])

    @commands.guild_only()
    @commands.group(name="uploadstreaks")
    async def _upload_streaks(self, ctx: commands.Context):
        """UploadStreaks Settings"""

    @commands.bot_has_permissions(embed_links=True)
    @_upload_streaks.command(name="list")
    async def _list(self, ctx: commands.Context):
        """List the current UploadStreaks challenges."""

        settings = await self.config.guild(ctx.guild).challenges()
        embed = discord.Embed(title=f"UploadStreaks Challenges", color=await ctx.embed_color())
        if not settings:
            embed.description = "No UploadStreaks Challenges Found"
        else:
            embed.description = ""
            for count, name in enumerate(settings.keys()):
                embed.description += f"**{count+1}.** {name}"
        return await ctx.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @_upload_streaks.command(name="leaderboard", aliases=['ldb'])
    async def _leaderboard(self, ctx: commands.Context, challenge: str, num=10):
        """See the current UploadStreaks leaderboard for a challenge."""

        settings = await self.config.guild(ctx.guild).challenges()
        if challenge not in settings.keys():
            return await ctx.send("No challenge was found with that name.")

        embed = discord.Embed(title=f"UploadStreaks Challenge `{challenge}`", color=await ctx.embed_color())
        if not settings[challenge]['users']:
            embed.description = "No users have participated in this challenge yet."
        else:
            embed.description = "```Streak   Points   User\n"
            ldb = sorted(settings[challenge]['users'].items(), key=lambda x: x[1][1], reverse=True)
            for i in range(min(num, len(ldb))):
                member = ctx.guild.get_member(int(ldb[i][0]))
                if member:
                    name = member.display_name
                else:
                    try:
                        name = (await self.bot.fetch_user(int(ldb[i][0]))).name
                    except discord.HTTPException:
                        continue
                embed.description += f"{(str(ldb[i][1][1])+settings[challenge]['streak']).center(6)}   {str(ldb[i][1][0]).center(6)}   {name}\n"
            embed.description += "```"
        return await ctx.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @_upload_streaks.command(name="user")
    async def _user(self, ctx: commands.Context, user: discord.Member):
        """See a user's UploadStreaks points."""

        settings = await self.config.guild(ctx.guild).challenges()
        embed = discord.Embed(title=f"UploadStreaks Info for {user.display_name}", color=await ctx.embed_color())
        if not settings:
            embed.description = "No UploadStreaks Challenges Found"
        else:
            for name, challenge in settings.items():
                u = challenge['users'].get(str(user.id))
                if u:
                    embed.add_field(name=f"Challenge `{name}`", inline=False, value=f"Points: {u[0]}\nStreak: {u[1]}{challenge['streak']}")
        if not embed.fields:
            embed.description = "This user has not participated in any UploadStreaks challenges."
        return await ctx.send(embed=embed)

    @commands.admin()
    @_upload_streaks.group(name="settings")
    async def _settings(self, ctx: commands.Context):
        """UploadStreaks Settings"""

    @_settings.command(name="new")
    async def _settings_new(self, ctx: commands.Context, challenge: str, streak_name: str, interval: int, utc_day_start: int, credits: typing.Optional[int] = 0, role: typing.Optional[discord.Role] = None, *channels: discord.TextChannel):
        """
        Start a new UploadStreaks challenge. See below for paramters:

        `challenge`: the name of the challenge
        `streak_name`: the name of the streak (e.g. `d` for days)
        `interval`: a number representing the length in days for each interval (e.g. `5`)
        `utc_day_start`: a number representing the UTC hour to start the day on (e.g. `2` or `23`)
        `credits`: the amount of credits to be awarded to a user on post (optional, default 0)
        `role`: the role to automatically detect challenge entries from (leave empty for everyone)
        `channels`: the channels to listen in for entries
        """

        # Test utc_day_start
        if not(0 <= utc_day_start < 24):
            return await ctx.send(f"`{utc_day_start}` is not a valid hour (in 24-hr format)!")

        # Convert interval
        if interval <= 0:
            return await ctx.send(f"`{interval}` is not a positive integer!")

        if datetime.utcnow().hour < utc_day_start:
            ts = datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=utc_day_start, tzinfo=timezone.utc).timestamp()
        else:
            ts = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0, second=0, minute=0, hour=utc_day_start, tzinfo=timezone.utc).timestamp()

        # Test credit amount
        if credits < 0:
            return await ctx.send("The amount of credits must be a positive integer!")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            challenges[challenge] = {
                "active": True,
                "streak": streak_name,
                "interval": (interval, ts, utc_day_start),
                "credits": credits,
                "role": role.id if role else None,
                "channels": [c.id for c in channels],
                "users": {}
            }

        starts_in = datetime.utcfromtimestamp(ts) - datetime.utcnow()

        return await ctx.send(f"A new challenge `{challenge}` was successfully added! If you want to edit anything, use `{ctx.clean_prefix}uploadstreaks settings edit`. The challenge will start in {starts_in.seconds//3600} hrs {(starts_in.seconds//60)%60} mins at {datetime.utcfromtimestamp(ts)} UTC.")

    @_settings.command(name="toggle")
    async def _settings_toggle(self, ctx: commands.Context, challenge_name: str, true_or_false: bool):
        """
        Toggle whether an UploadStreaks challenge is active.

        **Warning:** this *may* break users' streaks if a challenge is toggled off for longer than the interval.
        """

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["active"] = true_or_false

        return await ctx.tick()

    @_settings.command(name="reset")
    async def _settings_reset(self, ctx: commands.Context, challenge_name: str, enter_true_to_confirm: bool):
        """Reset all streaks & points of an UploadStreaks challenge."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["users"] = {}

        return await ctx.tick()

    @_settings.command(name="delete")
    async def _settings_delete(self, ctx: commands.Context, challenge_name: str, enter_true_to_confirm: bool):
        """Delete an UploadStreaks challenge."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            del challenges[challenge_name]

        return await ctx.tick()

    @_settings.group(name="edit")
    async def _settings_edit(self, ctx: commands.Context):
        """Edit an UploadStreaks Challenge"""

    @_settings_edit.command(name="streakname")
    async def _settings_edit_streak_name(self, ctx: commands.Context, challenge_name: str, streak_name: str):
        """Edit the name of the streak for an UploadStreaks challenge."""

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["streak"] = streak_name

        return await ctx.tick()

    @_settings_edit.command(name="interval")
    async def _settings_edit_interval(self, ctx: commands.Context, challenge_name: str, interval: int, utc_day_start: int):
        """Edit the interval of an UploadStreaks challenge."""

        # Convert interval
        if interval <= 0:
            return await ctx.send(f"`{interval}` is not a positive integer!")

        # Test utc_day_start
        if not (0 <= utc_day_start < 24):
            return await ctx.send(f"`{utc_day_start}` is not a valid hour (in 24-hr format)!")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["interval"] = (interval, challenges[challenge_name]["interval"][1], utc_day_start)

        return await ctx.tick()

    @_settings_edit.command(name="credits")
    async def _settings_edit_credits(self, ctx: commands.Context, challenge_name: str, credits: int):
        """Edit the awarded credits of an UploadStreaks challenge."""

        if credits < 0:
            return await ctx.send("The amount of credits must be a positive integer!")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["credits"] = credits

        return await ctx.tick()

    @_settings_edit.command(name="role")
    async def _settings_edit_role(self, ctx: commands.Context, challenge_name: str, role: discord.Role = None):
        """Edit the role of an UploadStreaks challenge (leave empty for everyone)."""

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["role"] = role.id if role else None

        return await ctx.tick()

    @_settings_edit.command(name="channels")
    async def _settings_edit_channels(self, ctx: commands.Context, challenge_name: str, *channels: discord.TextChannel):
        """Edit the channels of an UploadStreaks challenge."""

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            challenges[challenge_name]["channels"] = [c.id for c in channels]

        return await ctx.tick()

    @_settings.group(name="set")
    async def _settings_set(self, ctx: commands.Context):
        """Manually Set User Streaks & Points"""

    @_settings_set.command(name="points")
    async def _settings_set_points(self, ctx: commands.Context, user: discord.Member, challenge_name: str, points: int):
        """Manually set a user's points in an UploadStreaks challenge."""

        if points < 1:
            return await ctx.send("The points must be at least `1`!")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            orig = challenges[challenge_name]['users'].get(str(user.id))

            if not orig:
                return await ctx.send("That user has not participated in the challenge yet!")

            challenges[challenge_name]['users'][str(user.id)] = (points, orig[1], orig[2])

        return await ctx.tick()

    @_settings_set.command(name="streak")
    async def _settings_set_streak(self, ctx: commands.Context, user: discord.Member, challenge_name: str, streak: int):
        """Manually set a user's streak in an UploadStreaks challenge."""

        if streak < 1:
            return await ctx.send("The streak must be at least `1`!")

        async with self.config.guild(ctx.guild).challenges() as challenges:
            if challenge_name not in challenges.keys():
                return await ctx.send("There was no UploadStreaks challenge found with that name!")

            orig = challenges[challenge_name]['users'].get(str(user.id))

            if not orig:
                return await ctx.send("That user has not participated in the challenge yet!")

            challenges[challenge_name]['users'][str(user.id)] = (orig[0], streak, orig[2])

        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @_settings.command(name="view")
    async def _settings_view(self, ctx: commands.Context):
        """View the settings of UploadStreaks challenges in this server."""

        settings = await self.config.guild(ctx.guild).challenges()
        embed = discord.Embed(title="UploadStreaks Settings", color=await ctx.embed_color())
        if not settings:
            embed.description = "No UploadStreaks Challenges Found"
        else:
            for name, challenge in settings.items():
                channels = []
                for c in challenge['channels']:
                    if ch := ctx.guild.get_channel(c):
                        channels.append(ch.mention)

                embed.add_field(
                    name=f"Challenge `{name}`",
                    inline=False,
                    value=f"""
                    **Active:** {challenge['active']}
                    **Streak Name:** {challenge['streak']}
                    **Interval:** {challenge['interval'][0]} days (started on {datetime.utcfromtimestamp(challenge['interval'][1])})
                    **Credits:** {challenge['streak']}
                    **Role:** {ctx.guild.get_role(challenge['role']).mention if challenge['role'] and ctx.guild.get_role(challenge['role']) else None }
                    **Channels:** {humanize_list(channels)}
                    """
                )
        return await ctx.send(embed=embed)

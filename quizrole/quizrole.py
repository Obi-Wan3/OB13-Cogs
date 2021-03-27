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

import time
import typing
import random
import asyncio
from datetime import datetime, timedelta

import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate
from .converters import ExplicitNone, PositiveInteger


class QuizRole(commands.Cog):
    """
    Take a Quiz to Gain a Role

    Automatically assign roles to users who have taken and successfully passed a quiz through DMs.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": False,
            "logchannel": None,
            "quizzes": {},
        }
        default_member = {
            "taken": {}
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

    @commands.guild_only()
    @commands.command(name="quizrole")
    async def _quizrole(self, ctx: commands.Context, quiz_name):
        """Take a quiz to gain a role in this server!"""

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if not await self.config.guild(ctx.guild).toggle():
            return ctx.send("QuizRole is toggled off for this server.", delete_after=15)

        quiz = (await self.config.guild(ctx.guild).quizzes()).get(quiz_name)
        if not quiz:
            return await ctx.send(f"No quiz was found with this name. To see all available quizzes, run `{ctx.clean_prefix}quizroles`.", delete_after=15)

        if quiz['role'] in [r.id for r in ctx.author.roles]:
            return await ctx.send("You already have this role!", delete_after=15)

        if quiz['req'] and not (quiz['req'] in [r.id for r in ctx.author.roles]):
            return await ctx.send("You do not have the required role to take this quiz!", delete_after=15)

        randomize = quiz['randomize']
        if randomize is True:
            questions = quiz['questions']
            random.shuffle(questions)
        elif randomize is False:
            questions = quiz['questions']
        else:
            questions = random.choices(quiz['questions'], k=randomize)

        time_limit = quiz['timelimit']*60
        min_time = 2*time_limit//len(questions)
        role = ctx.guild.get_role(quiz['role'])
        if not role:
            return await ctx.send("Error: The role tied to this quiz no longer exists.", delete_after=15)

        try:
            await ctx.author.send(f"You are about to take the quiz `{quiz_name}` to get {role.name}. Please type `start` to get started, or `cancel` to cancel. There will be {len(questions)} questions, and you will have {int(time_limit/60)} minutes to complete it (at most {min_time} seconds per question). Once you start, you cannot cancel.")
        except discord.HTTPException:
            return await ctx.send(f"{ctx.author.mention} I cannot DM you!", delete_after=30)

        pred = MessagePredicate.lower_contained_in(['cancel', 'start'], channel=ctx.author.dm_channel, user=ctx.author)
        try:
            await self.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.author.send("The operation has timed out. Please try again.")

        if pred.result == 0:
            return await ctx.author.send("Quiz cancelled.")

        async with self.config.member(ctx.author).taken() as attempts:
            if quiz_name in attempts.keys():
                last_attempt = attempts[quiz_name]
                if datetime.fromtimestamp(last_attempt) > datetime.now() - timedelta(days=quiz['cooldown']):
                    return await ctx.author.send(f"Please wait before taking this QuizRole again! The cooldown is {quiz['cooldown']} days, and you last took this {round((time.time()-int(last_attempt))/86400, 1)} days ago.")
            attempts[quiz_name] = time.time()

        start_time = time.time()
        score = 0
        for question in questions:
            await ctx.author.send(question[0])
            try:
                resp = await self.bot.wait_for("message", check=MessagePredicate.same_context(channel=ctx.author.dm_channel, user=ctx.author), timeout=min_time)
                if time.time() > start_time + time_limit:
                    await ctx.author.send( f"You have exceeded the time limit for this quiz.")
                    break
                if resp.content.lower() == question[1].lower():
                    score += 1
            except asyncio.TimeoutError:
                return await ctx.author.send(f"Unfortunately, you have exceeded the time limit for this question. Please try again in {quiz['cooldown']} days.")

        logchannel = await self.config.guild(ctx.guild).logchannel()
        if score >= quiz['minscore']:
            try:
                await ctx.author.add_roles(role, reason=f"QuizRole: Passed `{quiz_name}` with a score of {score}/{len(questions)}.")
            except discord.HTTPException:
                return await ctx.author.send("Something went wrong when assigning your role.")
            if logchannel:
                try:
                    await self.bot.get_channel(logchannel).send(f"{ctx.author.mention} has passed `{quiz_name}` with a score of {score}/{len(questions)}.")
                except discord.HTTPException:
                    pass
            return await ctx.author.send(f"Congratulations! You have passed the quiz `{quiz_name}` with a score of {score}/{len(questions)}, and have received the role {role.name}.")
        else:
            if logchannel:
                try:
                    await self.bot.get_channel(logchannel).send(f"{ctx.author.mention} did not pass `{quiz_name}` with a score of {score}/{len(questions)}.")
                except discord.HTTPException:
                    pass
            return await ctx.author.send(f"Unfortunately, you did not pass the quiz `{quiz_name}`; the minimum score was {quiz['minscore']}/{len(questions)} and you received a score of {score}/{len(questions)}.")

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command(name="quizroles")
    async def _quizroles(self, ctx: commands.Context):
        """List all available quizzes in this server."""

        settings = await self.config.guild(ctx.guild).all()
        if not settings['toggle']:
            return await ctx.send("QuizRole is currently toggled off for this server.")
        embed = discord.Embed(title=f"QuizRoles for {ctx.guild.name}", color=await ctx.embed_color())
        for quiz_name, quiz in settings['quizzes'].items():
            if (quiz['req'] is None or quiz['req'] in [r.id for r in ctx.author.roles]) and quiz['enabled']:
                val = f"""
                        **Role:** {ctx.guild.get_role(quiz['role']).mention if ctx.guild.get_role(quiz['role']) else None}
                        **Requirement:** {ctx.guild.get_role(quiz['req']).mention if quiz['req'] and ctx.guild.get_role(quiz['req']) else None}
                        **Min. Score:** {quiz['minscore']}/{len(quiz['questions']) if quiz['randomize'] in (True, False) else quiz['randomize']}
                        **Time Limit:** {quiz['timelimit']} minutes
                        **Cooldown:** {quiz['cooldown']} days
                        **# Questions:** {len(quiz['questions']) if quiz['randomize'] in (True, False) else quiz['randomize']}
                        """
                embed.add_field(name=f'Quiz "{quiz_name}"', value=val)
        if len(embed.fields) == 0:
            return await ctx.send("There are currently no available QuizRoles for you to take.")
        return await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="quizroleset")
    async def _quizroleset(self, ctx: commands.Context):
        """QuizRole Settings"""

    @_quizroleset.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle QuizRole on this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_quizroleset.command(name="logchannel")
    async def _log_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the QuizRole logchannel on this server (leave blank for no logchannel)."""
        if channel:
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(f"I cannot send messages to {channel.mention}!")
            await self.config.guild(ctx.guild).logchannel.set(channel.id)
        else:
            await self.config.guild(ctx.guild).logchannel.set(channel)
        return await ctx.tick()

    @commands.bot_has_permissions(manage_roles=True)
    @_quizroleset.command(name="newquiz")
    async def _new_quiz(
            self,
            ctx: commands.Context,
            name: str,
            role: discord.Role,
            req: typing.Union[discord.Role, ExplicitNone],
            numquestions: PositiveInteger,
            minscore: PositiveInteger,
            timelimit: PositiveInteger,
            cooldown: int,
            randomize: typing.Union[bool, PositiveInteger]
    ):
        """
        Add a new QuizRole for this server (interactive). See below for initial parameters:

        `name`: name of the quiz
        `role`: role to award upon completion
        `req`: a required role or `None`
        `numquestions`: how many questions the quiz will have
        `minscore`: the minimum # of correct answers a user must get
        `timelimit`: the time limit, expressed in minutes, for the quiz to be finished (maximum is 60 minutes)
        `cooldown`: the cooldown, expressed in days, for taking the quiz (put `0` for no cooldown)
        `randomize`: whether to randomize the order of the questions (true/false or an integer to choose that amount of questions randomly)
        """

        if minscore > numquestions:
            return await ctx.send("The minimum score cannot be greater than the # of questions!")

        if type(randomize) == int and randomize > numquestions:
            return await ctx.send("The # of randomized questions to select cannot be greater than the # of questions!")

        if role >= ctx.guild.me.top_role or (role >= ctx.author.top_role and ctx.author != ctx.guild.owner):
            return await ctx.send("That role cannot be assigned due to the Discord role hierarchy.")

        await ctx.send("Alright, please enter the questions and answers as I ask you, one by one (type `cancel` at any time to cancel): ")
        questions = []
        for i in range(numquestions):
            await ctx.send(f"Please enter question {i+1}:")
            resp0 = await self.bot.wait_for("message", check=MessagePredicate.same_context(ctx))
            if resp0.content == 'cancel':
                return await ctx.send("Alright, you have cancelled the creation of this quiz.")
            await ctx.send(f"Please enter the accepted answer for question {i + 1}:")
            resp1 = await self.bot.wait_for("message", check=MessagePredicate.same_context(ctx))
            if resp1.content == 'cancel':
                return await ctx.send("Alright, you have cancelled the creation of this quiz.")
            questions.append((resp0.content, resp1.content))

        quiz = {
            "enabled": False,
            "role": role.id,
            "req": req.id if req else None,
            "minscore": minscore,
            "timelimit": timelimit,
            "cooldown": cooldown,
            "randomize": randomize,
            "questions": questions
        }
        async with self.config.guild(ctx.guild).quizzes() as quizzes:
            quizzes[name] = quiz

        return await ctx.send(f"The quiz has been successfully added! View the quizzes with `{ctx.clean_prefix}quizroleset view`. To allow this quiz to be taken, enable it first with `{ctx.clean_prefix}quizroleset edit <quiz> enabled true`.")

    @commands.bot_has_permissions(manage_roles=True)
    @_quizroleset.command(name="edit")
    async def _edit(self, ctx: commands.Context, quiz_name: str, field: str, *, new_value: str):
        """
        Edit a QuizRole for this server.

        Valids fields are the same as the parameter names used in `[p]quizroleset add`, except for `numquestions`.
        To enable/disable a quiz, enter as the field `enabled` and the value true or false.
        If editing a question or answer, put `q1` or `a1`, for example, to edit the question or answer for the first question (as listed in `[p]quizroleset view`), respectively.
        """

        # Check if quiz_name is valid
        quizzes = await self.config.guild(ctx.guild).quizzes()
        if quiz_name not in quizzes.keys():
            return await ctx.send("There was no quiz found with that name!")

        if field.lower() == "enabled":
            if new_value.lower() in ("true", "yes"):
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["enabled"] = True
                return await ctx.send(f"The quiz `{quiz_name}` has been enabled.")
            elif new_value.lower() in ("false", "no"):
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["enabled"] = False
                return await ctx.send(f"The quiz `{quiz_name}` has been disabled.")

        elif field.lower() == "role":
            try:
                role = await commands.RoleConverter().convert(ctx=ctx, argument=new_value)
                if role >= ctx.guild.me.top_role or role >= ctx.author.top_role:
                    return await ctx.send("That role cannot be assigned due to the Discord role hierarchy.")
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["role"] = role.id
                return await ctx.send(f"The role for quiz `{quiz_name}` has been set to {role.mention}.")
            except commands.BadArgument:
                return await ctx.send(f"Failed to convert {new_value} to a role.")

        elif field.lower() == "req":
            if new_value.lower() == "none":
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["req"] = None
                return await ctx.send(f"The role requirement for quiz `{quiz_name}` has been set to None.")
            try:
                role = await commands.RoleConverter().convert(ctx=ctx, argument=new_value)
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["req"] = role.id
                return await ctx.send(f"The role requirement for quiz `{quiz_name}` has been set to {role.mention}.")
            except commands.BadArgument:
                return await ctx.send(f"Failed to convert {new_value} to a role.")

        elif field.lower() == "minscore":
            try:
                minscore = int(new_value)
            except ValueError:
                return await ctx.send(f"Failed to convert {new_value} to an integer.")
            if minscore > len(quizzes[quiz_name]["questions"]):
                return await ctx.send("The minimum score cannot be greater than the # of questions!")
            async with self.config.guild(ctx.guild).quizzes() as quizzes:
                quizzes[quiz_name]["minscore"] = minscore
            return await ctx.send(f"The minimum score for quiz `{quiz_name}` has been set to {minscore}.")

        elif field.lower() in ("timelimit", "cooldown"):
            try:
                time0 = int(new_value)
            except ValueError:
                return await ctx.send(f"Failed to convert {new_value} to an integer.")
            if field.lower() == "timelimit" and not 0 < time0 <= 60:
                return await ctx.send(f"The time limit should be an integer between 0 and 60 (minutes)")
            async with self.config.guild(ctx.guild).quizzes() as quizzes:
                quizzes[quiz_name][field.lower()] = time0
            return await ctx.send(f"The {field.lower()} for quiz `{quiz_name}` has been set to {time0}.")

        elif field.lower() == "randomize":
            if new_value.lower() in ("true", "yes"):
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["randomize"] = True
                return await ctx.send(f"Randomization for quiz `{quiz_name}` has been enabled.")
            elif new_value.lower() in ("false", "no"):
                async with self.config.guild(ctx.guild).quizzes() as quizzes:
                    quizzes[quiz_name]["randomize"] = False
                return await ctx.send(f"Randomization for quiz `{quiz_name}` has been disabled.")
            try:
                randomize = int(new_value)
            except ValueError:
                return await ctx.send(f"Failed to convert {new_value} to an integer.")
            if randomize > len(quizzes[quiz_name]["questions"]):
                return await ctx.send("The # questions to randomly choose cannot be greater than the # of questions!")
            async with self.config.guild(ctx.guild).quizzes() as quizzes:
                quizzes[quiz_name]["randomize"] = randomize
            return await ctx.send(f"Quiz `{quiz_name}` will now have {randomize} randomly selected questions.")

        elif len(field) >= 2 and field.lower()[0] == "q" and field.lower()[1:].isdigit():
            async with self.config.guild(ctx.guild).quizzes() as quizzes:
                quizzes[quiz_name]["questions"][int(field[1:])-1][0] = new_value
            return await ctx.send(f"Question #{int(field[1:])} has been set to `{new_value}`.")

        elif len(field) >= 2 and field.lower()[0] == "a" and field.lower()[1:].isdigit():
            async with self.config.guild(ctx.guild).quizzes() as quizzes:
                quizzes[quiz_name]["questions"][int(field[1:])-1][1] = new_value
            return await ctx.send(f"Answer #{int(field[1:])} has been set to `{new_value}`.")

        else:
            return await ctx.send("Invalid field name.")

    @_quizroleset.command(name="addquestion")
    async def _add_question(self, ctx: commands.Context, quiz_name: str, *, question_and_answer: str):
        """
        Add a new question to a QuizRole in this server.

        For the question_and_answer field, please input the question and then the answer, separated by 2 slashes `//`.
        """

        async with self.config.guild(ctx.guild).quizzes() as quizzes:
            if quiz_name not in quizzes.keys():
                return await ctx.send("There was no quiz found with that name!")

            separated = question_and_answer.split("//")
            if not len(separated) > 1:
                return await ctx.send("Please separate the question and answer with `//`.")

            quizzes[quiz_name]["questions"].append((separated[0].strip(), separated[1].strip()))

        return await ctx.send(f"A new question `{separated[0].strip()}` has been added with answer `{separated[1].strip()}`.")

    @_quizroleset.command(name="removequestion")
    async def _remove_question(self, ctx: commands.Context, quiz_name: str, question_number: int):
        """Remove a question from a QuizRole in this server."""

        async with self.config.guild(ctx.guild).quizzes() as quizzes:
            if quiz_name not in quizzes.keys():
                return await ctx.send("There was no quiz found with that name!")

            removed = quizzes[quiz_name]["questions"].pop(question_number-1)

        return await ctx.send(f"Removed question `{removed[0]}` with answer `{removed[1]}`.")

    @_quizroleset.command(name="removequiz")
    async def _remove_quiz(self, ctx: commands.Context, quiz_name: str, enter_true_to_confirm: bool):
        """Remove a QuizRole from this server."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).quizzes() as quizzes:
            if quiz_name not in quizzes.keys():
                return await ctx.send("There was no quiz found with that name!")

            del quizzes[quiz_name]

        return await ctx.send(f"Quiz `{quiz_name}` was removed from this server's QuizRoles.")

    @commands.bot_has_permissions(embed_links=True)
    @_quizroleset.command(name="view", aliases=["list"])
    async def _view(self, ctx: commands.Context):
        """View QuizRole settings for this server."""
        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="QuizRole Settings", color=await ctx.embed_color(), description=f"**Toggle** (Overrides Enabled Statuses): {settings['toggle']}\n**Log Channel:** {self.bot.get_channel(settings['logchannel']).mention if settings['logchannel'] else None}")
        for quiz_name, quiz in settings['quizzes'].items():
            val = f"""
            **Enabled:**: {quiz['enabled']}
            **Role:** {ctx.guild.get_role(quiz['role']).mention if ctx.guild.get_role(quiz['role']) else None}
            **Requirement:** {ctx.guild.get_role(quiz['req']).mention if quiz['req'] and ctx.guild.get_role(quiz['req']) else None}
            **Min. Score:** {quiz['minscore']}/{len(quiz['questions']) if quiz['randomize'] in (True, False) else quiz['randomize']}
            **Time Limit:** {quiz['timelimit']} minutes
            **Cooldown:** {quiz['cooldown']} days
            **Randomize:** {quiz['randomize']}
            **Questions (Answers):**
            """
            for i, q in enumerate(quiz['questions']):
                val += f"{i+1}. `{q[0]}` (`{q[1]}`)\n"
            embed.add_field(name=f'Quiz "{quiz_name}"', value=val)
        return await ctx.send(embed=embed)

from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord


class RestrictedRolePerms(commands.Cog):
    """
    Restricted Permissions for Roles

    Gives restricted permissions to certain roles to mention/assign other roles.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "mentionable": {"toggle": False, "rules": {}, "message": None},
            "assignable": {"toggle": False, "rules": {}, "message": None}
        }
        self.config.register_guild(**default_guild)

    @staticmethod
    async def _has_rule(rules, author_roles, role1):
        perms = False
        for ar in author_roles:
            found = rules.get(ar)
            if found and role1 in found:
                perms = True
        print(rules.keys(), author_roles)
        return perms

    @commands.guild_only()
    @commands.group(name="rrp")
    async def _rrp(self, ctx: commands.Context):
        """RestrictedRolePerms Commands"""

    @_rrp.command(name="allowmentions")
    async def _allow_mentions(self, ctx: commands.Context, role: discord.Role):
        """Set a role to be mentionable."""
        rules = await self.config.guild(ctx.guild).mentionable()

        if not rules['toggle']:
            return await ctx.send("The mentionability feature is toggled off for this server.")

        if not await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to toggle mentionability for {role.mention}.")

        try:
            await role.edit(mentionable=True, reason=f"RRP: toggled by {ctx.author.display_name}#{ctx.author.discriminator}")
        except discord.Forbidden:
            return await ctx.send("I do not have permissions to edit this role!")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while editing this role.")

        return await ctx.send(f"{role.mention} has been set to be mentionable by everyone.")

    @_rrp.command(name="denymentions")
    async def _deny_mentions(self, ctx: commands.Context, role: discord.Role):
        """Set a role to be non-mentionable."""
        rules = await self.config.guild(ctx.guild).mentionable()

        if not rules['toggle']:
            return await ctx.send("The mentionability feature is toggled off for this server.")

        if not await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to toggle mentionability for {role.mention}.")

        try:
            await role.edit(mentionable=False, reason=f"RRP: toggled by {ctx.author.display_name}#{ctx.author.discriminator}")
        except discord.Forbidden:
            return await ctx.send("I do not have permissions to edit this role!")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while editing this role.")

        return await ctx.send(f"{role.mention} has been set to be not mentionable by everyone.")

    @_rrp.command(name="assignrole")
    async def _assign_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Assign a role to a member."""
        rules = await self.config.guild(ctx.guild).assignable()

        if not rules['toggle']:
            return await ctx.send("The role assignment feature is toggled off for this server.")

        if not await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to assign {role.mention}.")

        try:
            await member.add_roles(role, reason=f"RRP: assigned by {ctx.author.display_name}#{ctx.author.discriminator}")
        except discord.Forbidden:
            return await ctx.send("I do not have permissions to assign this role!")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while assigning this role.")

        return await ctx.send(f"{role.mention} has been assigned to {member.mention}.")

    @_rrp.command(name="removerole")
    async def _remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Remove a role from a member."""
        rules = await self.config.guild(ctx.guild).assignable()

        if not rules['toggle']:
            return await ctx.send("The role assignment feature is toggled off for this server.")

        if not await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to assign {role.mention}.")

        if role not in member.roles:
            return await ctx.send("The member did not have the role!")

        try:
            await member.remove_roles(role, reason=f"RRP: removed by {ctx.author.display_name}#{ctx.author.discriminator}")
        except discord.Forbidden:
            return await ctx.send("I do not have permissions to remove this role!")
        except discord.HTTPException:
            return await ctx.send("Something went wrong while removing this role.")

        return await ctx.send(f"{role.mention} has been removed from {member.mention}.")

    @commands.admin()
    @commands.guild_only()
    @commands.group(name="rrpset")
    async def _rrpset(self, ctx: commands.Context):
        """RestrictedRolePerms Settings"""

    @_rrpset.command(name="view", aliases=["viewrules"])
    async def _view(self, ctx: commands.Context):
        """View the current rules for RestrictedRolePerms."""
        rules = await self.config.guild(ctx.guild).all()
        mentionable = rules['mentionable']
        assignable = rules['assignable']

        e = discord.Embed(title="RestrictedRolePerms Rules", color=await ctx.embed_color())

        mentionable_rules = f"""
        **Toggle:** {mentionable["toggle"]}
        **Message:** {mentionable['message'] if mentionable['message'] else "Default"}
        **Rules:** {"None" if not mentionable['rules'] else ""}\n"""
        for r0, r1 in mentionable["rules"].items():
            mentionable_rules += f"{ctx.guild.get_role(int(r0)).name} can toggle mentionability for {humanize_list([ctx.guild.get_role(int(r2)) for r2 in r1])}"
        e.add_field(name="Mentionable", inline=False, value=mentionable_rules)

        assignable_rules = f"""
        **Toggle:** {assignable["toggle"]}
        **Message:** {assignable['message'] if assignable['message'] else "Default"}
        **Rules:** {"None" if not assignable['rules'] else ""}\n"""
        for r0, r1 in assignable["rules"].items():
            assignable_rules += f"{ctx.guild.get_role(int(r0)).name} can assign {humanize_list([ctx.guild.get_role(int(r2)) for r2 in r1])}"
        e.add_field(name="Assignable", inline=False, value=assignable_rules)

        return await ctx.send(embed=e)

    @_rrpset.group(name="addrule")
    async def _add_rule(self, ctx: commands.Context):
        """Add a rule to give certain roles restricted permissions."""

    @_add_rule.command(name="mentionable")
    async def _add_mentionable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, *roles_to_allow_to_be_made_mentionable: discord.Role):
        """Allow a certain role to make a few other roles mentionable through RRP."""

        async with self.config.guild(ctx.guild).mentionable.rules() as rules:
            if rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send("There is already a rule for that role! Please remove it first using `[p]rrpset removerule`.")
            rules[str(role_to_give_perms_to.id)] = [r.id for r in roles_to_allow_to_be_made_mentionable]

        return await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to toggle mentionability for {humanize_list([r.mention for r in roles_to_allow_to_be_made_mentionable])}")

    @_add_rule.command(name="assignable")
    async def _add_assignable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, *roles_to_allow_to_be_assigned: discord.Role):
        """Allow a certain role to assign a few other roles through RRP."""

        async with self.config.guild(ctx.guild).assignable.rules() as rules:
            if rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send("There is already a rule for that role! Please remove it first using `[p]rrpset removerule`.")
            rules[str(role_to_give_perms_to.id)] = [r.id for r in roles_to_allow_to_be_assigned]

        return await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to assign {humanize_list([r.mention for r in roles_to_allow_to_be_assigned])}")

    @_rrpset.group(name="removerule")
    async def _remove_rule(self, ctx: commands.Context):
        """Remove a rule to give certain roles restricted permissions."""

    @_remove_rule.command(name="mentionable")
    async def _rem_mentionable(self, ctx: commands.Context, role: discord.Role):
        """Disallow a certain role to make a few other roles mentionable through RRP."""

        async with self.config.guild(ctx.guild).mentionable.rules() as rules:
            if not rules.get(str(role.id)):
                return await ctx.send("There weren't any mentionability rules for that role!")
            del rules[str(role.id)]

        return await ctx.send(f"The mentionability rule for {role.mention} has been removed.")

    @_remove_rule.command(name="assignable")
    async def _rem_assignable(self, ctx: commands.Context, role: discord.Role):
        """Disallow a certain role to assign a few other roles through RRP."""

        async with self.config.guild(ctx.guild).assignable.rules() as rules:
            if not rules.get(str(role.id)):
                return await ctx.send("There weren't any assignability rules for that role!")
            del rules[str(role.id)]

        return await ctx.send(f"The assignability rule for {role.mention} has been removed.")

    @_rrpset.group(name="toggle")
    async def _toggle(self, ctx: commands.Context):
        """Toggle whether each RRP feature is active."""

    @_toggle.command(name="mentionable")
    async def _toggle_mentionable(self, ctx: commands.Context, true_or_false: bool):
        """Toggle RRP mentionability commands."""
        await self.config.guild(ctx.guild).mentionable.toggle.set(true_or_false)
        return await ctx.tick()

    @_toggle.command(name="assignable")
    async def _toggle_assignable(self, ctx: commands.Context, true_or_false: bool):
        """Toggle RRP role assignment commands."""
        await self.config.guild(ctx.guild).assignable.toggle.set(true_or_false)
        return await ctx.tick()

    @_rrpset.group(name="norulemessage")
    async def _no_rule_message(self, ctx: commands.Context):
        """Customize the error message sent when no rules are found giving the user restricted permissions."""

    @_no_rule_message.command(name="mentionable")
    async def _no_rule_message_mentionable(self, ctx: commands.Context, *, message: str = None):
        """Customize the mentionability error message (leave empty to reset)."""
        await self.config.guild(ctx.guild).mentionable.message.set(message)
        return await ctx.tick()

    @_no_rule_message.command(name="assignable")
    async def _no_rule_message_assignable(self, ctx: commands.Context, *, message: str = None):
        """Customize the role assignment error message (leave empty to reset)."""
        await self.config.guild(ctx.guild).assignable.message.set(message)
        return await ctx.tick()

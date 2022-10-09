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

import typing

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify

from .converters import ExplicitAll


class RestrictedRolePerms(commands.Cog):
    """
    Restricted Permissions for Roles

    Gives restricted permissions to certain roles to mention/assign other roles.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "mentionable": {"toggle": False, "rules": {}, "message": None, "success": None},
            "assignable": {"toggle": False, "rules": {}, "message": None, "success": None}
        }
        self.config.register_guild(**default_guild)

    @staticmethod
    async def _has_rule(rules, author_roles, role1):
        perms = False
        for ar in author_roles:
            if found := rules.get(ar):
                if role1 in found:
                    perms = True
                elif "all" in found:
                    perms = None
        return perms

    @commands.bot_has_permissions(manage_roles=True)
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

        has_perms = await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id)
        if (has_perms is False) or (has_perms is None and role >= ctx.author.top_role):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to toggle mentionability for {role.mention}.")

        if role < ctx.guild.me.top_role:
            await role.edit(mentionable=True, reason=f"RRP: toggled by {ctx.author.display_name}#{ctx.author.discriminator}")
        else:
            return await ctx.send("I do not have permissions to edit this role!")

        if rules['success']:
            return await ctx.send(rules['success'][0].replace("{role}", role.name).replace("{role.mention}", role.mention))

        return await ctx.send(f"{role.mention} has been set to be mentionable by everyone.")

    @_rrp.command(name="denymentions")
    async def _deny_mentions(self, ctx: commands.Context, role: discord.Role):
        """Set a role to be non-mentionable."""
        rules = await self.config.guild(ctx.guild).mentionable()

        if not rules['toggle']:
            return await ctx.send("The mentionability feature is toggled off for this server.")

        has_perms = await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id)
        if (has_perms is False) or (has_perms is None and role >= ctx.author.top_role):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to toggle mentionability for {role.mention}.")

        if role < ctx.guild.me.top_role:
            await role.edit(mentionable=False, reason=f"RRP: toggled by {ctx.author.display_name}#{ctx.author.discriminator}")
        else:
            return await ctx.send("I do not have permissions to edit this role!")

        if rules['success']:
            return await ctx.send(rules['success'][1].replace("{role}", role.name).replace("{role.mention}", role.mention))

        return await ctx.send(f"{role.mention} has been set to be not mentionable by everyone.")

    @_rrp.command(name="assignrole")
    async def _assign_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Assign a role to a member."""
        rules = await self.config.guild(ctx.guild).assignable()

        if not rules['toggle']:
            return await ctx.send("The role assignment feature is toggled off for this server.")

        has_perms = await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id)
        if (has_perms is False) or (has_perms is None and role >= ctx.author.top_role):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to assign {role.mention}.")

        if role in member.roles:
            return await ctx.send("The member already has the role!")

        if role < ctx.guild.me.top_role and role not in member.roles:
            await member.add_roles(role, reason=f"RRP: assigned by {ctx.author.display_name}#{ctx.author.discriminator}")
        else:
            return await ctx.send("I do not have permissions to assign this role!")

        if rules['success']:
            return await ctx.send(rules['success'][0].replace("{role}", role.name).replace("{role.mention}", role.mention).replace("{member}", f"{member.display_name}").replace("{member.mention}", member.mention))

        return await ctx.send(f"{role.mention} has been assigned to {member.mention}.")

    @_rrp.command(name="removerole")
    async def _remove_role(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Remove a role from a member."""
        rules = await self.config.guild(ctx.guild).assignable()

        if not rules['toggle']:
            return await ctx.send("The role assignment feature is toggled off for this server.")

        has_perms = await self._has_rule(rules['rules'], [str(r.id) for r in ctx.author.roles], role.id)
        if (has_perms is False) or (has_perms is None and role >= ctx.author.top_role):
            if rules['message']:
                return await ctx.send(rules['message'])
            return await ctx.send(f"Unfortunately, no rules were found allowing you to assign {role.mention}.")

        if role not in member.roles:
            return await ctx.send("The member did not have the role!")

        if role < ctx.guild.me.top_role:
            await member.remove_roles(role, reason=f"RRP: removed by {ctx.author.display_name}#{ctx.author.discriminator}")
        else:
            return await ctx.send("I do not have permissions to remove this role!")

        if rules['success']:
            return await ctx.send(rules['success'][1].replace("{role}", role.name).replace("{role.mention}", role.mention).replace("{member}", f"{member.display_name}").replace("{member.mention}", member.mention))

        return await ctx.send(f"{role.mention} has been removed from {member.mention}.")

    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.group(name="rrpset")
    async def _rrpset(self, ctx: commands.Context):
        """RestrictedRolePerms Settings"""

    @commands.bot_has_permissions(embed_links=True)
    @_rrpset.group(name="view", aliases=["rules"])
    async def _view(self, ctx: commands.Context):
        """View the current rules for RestrictedRolePerms."""

    @_view.command(name="mentionable")
    async def _view_mentionable(self, ctx: commands.Context, role: discord.Role = None):
        """View the mentionability rules for RestrictedRolePerms."""
        rules = await self.config.guild(ctx.guild).mentionable()

        if not role:
            rules_for_roles = []
            async with self.config.guild(ctx.guild).mentionable.rules() as config_rules:
                for r in config_rules.keys():
                    if ro := ctx.guild.get_role(int(r)):
                        rules_for_roles.append(ro.mention)
                    else:
                        del config_rules[r]

            desc = f"""
            **Toggle:** {rules["toggle"]}
            **Error Message:** {rules['message'] if rules['message'] else "Default"}
            **Success Message:** {f"{rules['success'][0]}, {rules['success'][1]}" if rules['success'] else "Default"}
            **Rules:** {"None" if not rules['rules'] else humanize_list(rules_for_roles)}"""

            return await ctx.send(embed=discord.Embed(
                title="RRP Mentionability Rules",
                color=await ctx.embed_color(),
                description=desc
            ))

        else:
            rules_for_role = rules["rules"].get(str(role.id))
            if not rules_for_role:
                return await ctx.send(f"No mentionability rules found for {role.mention}")
            if "all" in rules_for_role:
                await ctx.send(f"**{role.mention}** can toggle mentionability for all roles below it.")
            else:
                role_rules = []
                async with self.config.guild(ctx.guild).mentionable.rules() as config_rules:
                    for r in config_rules[str(role.id)]:
                        if ro := ctx.guild.get_role(int(r)):
                            role_rules.append(ro.mention)
                        else:
                            config_rules[str(role.id)].remove(r)

                for p in pagify(f"**{role.mention}** can toggle mentionability for {humanize_list(role_rules)}", delims=[", "]):
                    await ctx.send(p)

    @_view.command(name="assignable")
    async def _view_assignable(self, ctx: commands.Context, role: discord.Role = None):
        """View the assignability rules for RestrictedRolePerms."""
        rules = await self.config.guild(ctx.guild).assignable()

        if not role:
            rules_for_roles = []
            async with self.config.guild(ctx.guild).assignable.rules() as config_rules:
                for r in config_rules.keys():
                    if ro := ctx.guild.get_role(int(r)):
                        rules_for_roles.append(ro.mention)
                    else:
                        del config_rules[r]

            desc = f"""
                **Toggle:** {rules["toggle"]}
                **Error Message:** {rules['message'] if rules['message'] else "Default"}
                **Success Message:** {f"{rules['success'][0]}, {rules['success'][1]}" if rules['success'] else "Default"}
                **Rules:** {"None" if not rules['rules'] else humanize_list(rules_for_roles)}"""

            return await ctx.send(embed=discord.Embed(
                title="RRP Assignability Rules",
                color=await ctx.embed_color(),
                description=desc
            ))

        else:
            rules_for_role = rules["rules"].get(str(role.id))
            if not rules_for_role:
                return await ctx.send(f"No assignability rules found for {role.mention}")
            if "all" in rules_for_role:
                await ctx.send(f"**{role.mention}** can assign all roles below it.")
            else:
                role_rules = []
                async with self.config.guild(ctx.guild).assignable.rules() as config_rules:
                    for r in config_rules[str(role.id)]:
                        if ro := ctx.guild.get_role(int(r)):
                            role_rules.append(ro.mention)
                        else:
                            config_rules[str(role.id)].remove(r)

                for p in pagify(f"**{role.mention}** can assign {humanize_list(role_rules)}", delims=[", "]):
                    await ctx.send(p)

    @_rrpset.group(name="addrule")
    async def _add_rule(self, ctx: commands.Context):
        """Add a rule to give certain roles restricted permissions."""

    @_add_rule.command(name="mentionable")
    async def _add_mentionable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, *roles_to_allow_to_be_made_mentionable: typing.Union[discord.Role, ExplicitAll]):
        """
        Allow a certain role to make a few other roles mentionable through RRP.

        For `roles_to_allow_to_be_made_mentionable`, either input a list of roles or `all` to allow perms for all roles below the given role.
        """

        # Hierarchy checks
        if role_to_give_perms_to >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("The role you want to give perms to is above you in the role hierarchy!")
        if "all" not in roles_to_allow_to_be_made_mentionable:
            for rm in roles_to_allow_to_be_made_mentionable:
                if rm >= role_to_give_perms_to:
                    return await ctx.send(f"{rm.mention} is above {role_to_give_perms_to.mention} in the role hierarchy!")

        async with self.config.guild(ctx.guild).mentionable.rules() as rules:
            if rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send(f"There is already a rule for that role! Please remove it first using `{ctx.clean_prefix}rrpset removerule`.")
            if "all" not in roles_to_allow_to_be_made_mentionable:
                rules[str(role_to_give_perms_to.id)] = [r.id for r in roles_to_allow_to_be_made_mentionable]
                for resp in pagify(f"{role_to_give_perms_to.mention} is now allowed to toggle mentionability for {humanize_list([r.mention for r in roles_to_allow_to_be_made_mentionable])}", delims=[", "]):
                    await ctx.send(resp)
            else:
                rules[str(role_to_give_perms_to.id)] = ["all"]
                return await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to toggle mentionability for all roles below it.")

    @_add_rule.command(name="assignable")
    async def _add_assignable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, *roles_to_allow_to_be_assigned: typing.Union[discord.Role, ExplicitAll]):
        """
        Allow a certain role to assign a few other roles through RRP.

        For `roles_to_allow_to_be_assigned`, either input a list of roles or `all` to allow perms for all roles below the given role.
        """

        # Hierarchy checks
        if role_to_give_perms_to >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("The role you want to give perms to is above you in the role hierarchy!")
        if "all" not in roles_to_allow_to_be_assigned:
            for ra in roles_to_allow_to_be_assigned:
                if ra >= role_to_give_perms_to:
                    return await ctx.send(f"{ra.mention} is above {role_to_give_perms_to.mention} in the role hierarchy!")

        async with self.config.guild(ctx.guild).assignable.rules() as rules:
            if rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send(f"There is already a rule for that role! Please remove it first using `{ctx.clean_prefix}rrpset removerule`.")
            if "all" not in roles_to_allow_to_be_assigned:
                rules[str(role_to_give_perms_to.id)] = [r.id for r in roles_to_allow_to_be_assigned]
                for resp in pagify(f"{role_to_give_perms_to.mention} is now allowed to assign {humanize_list([r.mention for r in roles_to_allow_to_be_assigned])}", delims=[", "]):
                    await ctx.send(resp)
            else:
                rules[str(role_to_give_perms_to.id)] = ["all"]
                return await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to assign all roles below it.")

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

    @_rrpset.group(name="editrule")
    async def _edit_rule(self, ctx: commands.Context):
        """Edit a rule to give certain roles restricted permissions."""

    @_edit_rule.command(name="mentionable")
    async def _edit_mentionable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, true_or_false: bool, *roles_to_edit_mentionability: typing.Union[discord.Role, ExplicitAll]):
        """
        Edit a rule to allow a role to make a few other roles mentionable through RRP.

        For `true_or_false`, enter `true` for adding to a rule and `false` for removing from a rule.
        For `roles_to_allow_to_be_made_mentionable`, either input a list of roles or `all` to allow perms for all roles below the given role.
        """

        # Hierarchy checks
        if role_to_give_perms_to >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("The role you want to give perms to is above you in the role hierarchy!")
        if "all" not in roles_to_edit_mentionability:
            for rm in roles_to_edit_mentionability:
                if rm >= role_to_give_perms_to:
                    return await ctx.send(
                        f"{rm.mention} is above {role_to_give_perms_to.mention} in the role hierarchy!")

        async with self.config.guild(ctx.guild).mentionable.rules() as rules:
            if not rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send("There no rule for that role!")
            for role_to_edit in roles_to_edit_mentionability:
                if role_to_edit == "all":
                    if true_or_false:
                        if role_to_edit in rules[str(role_to_give_perms_to.id)]:
                            await ctx.send('Cannot add "all" as it was already in the rule.')
                            continue
                        rules[str(role_to_give_perms_to.id)].append("all")
                        await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to toggle mentionability for all roles below it.")
                    else:
                        if role_to_edit not in rules[str(role_to_give_perms_to.id)]:
                            await ctx.send('Cannot remove "all" as it was not in the rule.')
                            continue
                        rules[str(role_to_give_perms_to.id)].remove("all")
                        await ctx.send(f"{role_to_give_perms_to.mention} is no longer allowed to toggle mentionability for {role_to_edit.mention}")

                elif true_or_false:
                    if role_to_edit.id in rules[str(role_to_give_perms_to.id)]:
                        await ctx.send(f"Cannot add {role_to_edit.mention} as it was already in the rule.")
                        continue
                    rules[str(role_to_give_perms_to.id)].append(role_to_edit.id)
                    await ctx.send(f"{role_to_give_perms_to.mention} is now allowed to toggle mentionability for {role_to_edit.mention}")
                else:
                    if role_to_edit.id not in rules[str(role_to_give_perms_to.id)]:
                        await ctx.send(f"Cannot remove {role_to_edit.mention} as it was not in the rule.")
                        continue
                    rules[str(role_to_give_perms_to.id)].remove(role_to_edit.id)
                    await ctx.send(f"{role_to_give_perms_to.mention} is no longer allowed to toggle mentionability for {role_to_edit.mention}")

    @_edit_rule.command(name="assignable")
    async def _edit_assignable(self, ctx: commands.Context, role_to_give_perms_to: discord.Role, true_or_false: bool, *roles_to_edit_assignability: typing.Union[discord.Role, ExplicitAll]):
        """
        Edit a rule to allow a certain role to assign a few other roles through RRP.

        For `true_or_false`, enter `true` for adding to a rule and `false` for removing from a rule.
        For `roles_to_allow_to_be_assigned`, either input a list of roles or `all` to allow perms for all roles below the given role.
        """

        # Hierarchy checks
        if role_to_give_perms_to >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("The role you want to give perms to is above you in the role hierarchy!")
        if "all" not in roles_to_edit_assignability:
            for ra in roles_to_edit_assignability:
                if ra >= role_to_give_perms_to:
                    return await ctx.send(
                        f"{ra.mention} is above {role_to_give_perms_to.mention} in the role hierarchy!")

        async with self.config.guild(ctx.guild).assignable.rules() as rules:
            if not rules.get(str(role_to_give_perms_to.id)):
                return await ctx.send("There no rule for that role!")
            for role_to_edit in roles_to_edit_assignability:
                if role_to_edit == "all":
                    if true_or_false:
                        if role_to_edit in rules[str(role_to_give_perms_to.id)]:
                            await ctx.send('Cannot add "all" as it was already in the rule.')
                            continue
                        rules[str(role_to_give_perms_to.id)].append("all")
                        await ctx.send(
                            f"{role_to_give_perms_to.mention} is now allowed to assign all roles below it.")
                    else:
                        if role_to_edit not in rules[str(role_to_give_perms_to.id)]:
                            await ctx.send('Cannot remove "all" as it was not in the rule.')
                            continue
                        rules[str(role_to_give_perms_to.id)].remove("all")
                        await ctx.send(
                            f"{role_to_give_perms_to.mention} is no longer allowed to assign {role_to_edit.mention}")

                elif true_or_false:
                    if role_to_edit.id in rules[str(role_to_give_perms_to.id)]:
                        await ctx.send(f"Cannot add {role_to_edit.mention} as it was already in the rule.")
                        continue
                    rules[str(role_to_give_perms_to.id)].append(role_to_edit.id)
                    await ctx.send(
                        f"{role_to_give_perms_to.mention} is now allowed to assign {role_to_edit.mention}")
                else:
                    if role_to_edit.id not in rules[str(role_to_give_perms_to.id)]:
                        await ctx.send(f"Cannot remove {role_to_edit.mention} as it was not in the rule.")
                        continue
                    rules[str(role_to_give_perms_to.id)].remove(role_to_edit.id)
                    await ctx.send(
                        f"{role_to_give_perms_to.mention} is no longer allowed to assign {role_to_edit.mention}")

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

    @_rrpset.group(name="successmessage")
    async def _success_message(self, ctx: commands.Context):
        """Customize the error message sent when no rules are found giving the user restricted permissions."""

    @_success_message.command(name="mentionable")
    async def _success_message_mentionable(self, ctx: commands.Context, *, message: str = None):
        """
        Customize the mentionability success message (leave empty to reset).

        You can put in `{role}` or `{role.mention}`, which will be replaced with the role that is modified.
        Please format the message like so: `message for allowmentions//message for denymentions`.
        """
        if not message:
            await self.config.guild(ctx.guild).mentionable.success.set(None)
        else:
            success_messages = message.split("//")
            if not len(success_messages) > 1:
                return await ctx.send("Please separate the 2 messages with `//`.")
            await self.config.guild(ctx.guild).mentionable.success.set((success_messages[0].strip(), success_messages[1].strip()))
        return await ctx.tick()

    @_success_message.command(name="assignable")
    async def _success_message_assignable(self, ctx: commands.Context, *, message: str = None):
        """
        Customize the role assignment success message (leave empty to reset).

        You can put in `{role}` or `{role.mention}`, which will be replaced with the role that is assigned/removed.
        Also, you can put in `{member}` or `{member.mention}`, which will be replaced with the member.
        Please format the message like so: `message for assignrole//message for removerole`.
        """
        if not message:
            await self.config.guild(ctx.guild).mentionable.success.set(None)
        else:
            success_messages = message.split("//")
            if not len(success_messages) > 1:
                return await ctx.send("Please separate the 2 messages with `//`.")
            await self.config.guild(ctx.guild).assignable.success.set((success_messages[0].strip(), success_messages[1].strip()))
        return await ctx.tick()

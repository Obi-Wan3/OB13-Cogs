from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord
import typing


class TemplatePosts(commands.Cog):
    """Posts w/ Template Requirements"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": False,
            "templates": {},
            "dm": False,
            "ignore": {
                "roles": [],
                "users": []
            }
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_message")
    async def _message_listener(self, message: discord.Message):
        if not message.guild:
            return

        ignored = await self.config.guild(message.guild).ignore()

        # Ignore these messages
        if (
                await self.bot.cog_disabled_in_guild(self, message.guild) or  # Cog disabled in guild
                not await self.config.guild(message.guild).toggle() or  # TemplatePosts toggled off
                message.author.bot or  # Message author is a bot
                list(set([r.id for r in message.author.roles]) & set(ignored['roles'])) or  # Author has ignored role
                message.author.id in ignored['users']  # Author is in ignore list
        ):
            return

        templates = await self.config.guild(message.guild).templates()
        for template in templates.values():
            if template['channel'] == message.channel.id:
                if not template['toggle']:
                    return

                missing = []
                for f in template['fields']:
                    if f not in message.content:
                        missing.append(f)

                if missing:
                    await message.delete()

                    if template['message']:
                        to_send = template['message'].replace(
                            "{channel}", f"{message.channel.mention}"
                        ).replace(
                            "{fields}", f"{humanize_list([f'`{f}`' for f in template['fields']])}"
                        ).replace(
                            "{missing}", f"{humanize_list([f'`{f}`' for f in missing])}"
                        )

                        try:
                            if message.author.dm_channel is None:
                                await message.author.create_dm()
                            await message.author.dm_channel.send(to_send)
                        except discord.Forbidden:
                            return

                return

    @commands.guild_only()
    @commands.admin()
    @commands.group(name="templateposts")
    async def _template_posts(self, ctx: commands.Context):
        """
        Posts w/ Template Requirements

        Requires any messages in a channel which a template is set to follow that template (or be auto-removed).
        """

    @_template_posts.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle TemplatePosts for this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_template_posts.command(name="add")
    async def _add(self, ctx: commands.Context, template_name: str, channel: discord.TextChannel, *, fields: str):
        """
        Add a new template to this server.

        `fields` should be a list of different required fields, separated with a `;`.
        For example: `Name;Location;Needed Items;Time` will check for those 4 fields.
        """

        async with self.config.guild(ctx.guild).templates() as templates:
            if templates.get(template_name):
                return await ctx.send("There is already a template with that name! If you want to edit it, use `[p]templateposts edit`.")
            templates[template_name] = {
                "toggle": True,
                "channel": channel.id,
                "message": "",
                "fields": [s.strip() for s in fields.split(";")]
            }

        return await ctx.send(f"The template `{template_name}` has been added and activated in {channel.mention}. If you would like it to DM users that do not comply, use `[p]templateposts edit message {template_name} <message>`.")

    @_template_posts.group(name="edit")
    async def _edit(self, ctx: commands.Context):
        """Edit a TemplatePosts Template"""

    @_edit.command(name="toggle")
    async def _edit_toggle(self, ctx: commands.Context, template_name: str, true_or_false: bool):
        """Toggle a specific template on or off."""

        async with self.config.guild(ctx.guild).templates() as templates:
            if not templates.get(template_name):
                return await ctx.send("There is no template with that name!")
            templates[template_name]["toggle"] = true_or_false

        return await ctx.tick()

    @_edit.command(name="message")
    async def _edit_message(self, ctx: commands.Context, template_name: str, *, message: str = None):
        """
        Set the message to DM a user with if their post is deleted (leave blank to reset to no message).

        Your message can have the following items in it to be replaced: `{channel}`, `{fields}`, and `{missing}`.
        """

        async with self.config.guild(ctx.guild).templates() as templates:
            if not templates.get(template_name):
                return await ctx.send("There is no template with that name!")
            if message:
                templates[template_name]["message"] = message
            else:
                templates[template_name]["message"] = ""

        return await ctx.tick()

    @_edit.command(name="channel")
    async def _edit_channel(self, ctx: commands.Context, template_name: str, channel: discord.TextChannel):
        """Edit the channel for a template."""

        async with self.config.guild(ctx.guild).templates() as templates:
            if not templates.get(template_name):
                return await ctx.send("There is no template with that name!")
            templates[template_name]["channel"] = channel.id

        return await ctx.tick()

    @_edit.command(name="fields")
    async def _edit_fields(self, ctx: commands.Context, template_name: str, *, new_fields: str):
        """Update the required fields of a template."""

        async with self.config.guild(ctx.guild).templates() as templates:
            if not templates.get(template_name):
                return await ctx.send("There is no template with that name!")
            templates[template_name]["fields"] = [s.strip() for s in new_fields.split(";")]

        return await ctx.tick()

    @_template_posts.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, template_name: str, enter_true_to_confirm: bool):
        """Remove a template from this server."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).templates() as templates:
            if template_name in templates.keys():
                del templates[template_name]
                return await ctx.send(f"Template `{template_name}` was removed.")
            else:
                return await ctx.send("There were no templates found with that name! See the set templates with `[p]templateposts view`.")

    @_template_posts.group(name="ignore")
    async def _ignore(self, ctx: commands.Context):
        """Modify the Ignored Roles for TemplatePosts"""

    @_ignore.command(name="add")
    async def _ignore_add(self, ctx: commands.Context, role_or_user: typing.Union[discord.Role, discord.Member]):
        """Add to the list of roles/users to be ignored by TemplatePosts."""

        if isinstance(role_or_user, discord.Role):
            async with self.config.guild(ctx.guild).ignore.roles() as ignored:
                if role_or_user.id not in ignored:
                    ignored.append(role_or_user.id)
        elif isinstance(role_or_user, discord.Member):
            async with self.config.guild(ctx.guild).ignore.users() as ignored:
                if role_or_user.id not in ignored:
                    ignored.append(role_or_user.id)
        else:
            # Shouldn't happen
            return await ctx.send("Error: input not a role or user.")

        return await ctx.tick()

    @_ignore.command(name="remove", aliases=["delete"])
    async def _ignore_remove(self, ctx: commands.Context, role_or_user: typing.Union[discord.Role, discord.Member]):
        """Remove from the list of roles/users to be ignored by TemplatePosts."""

        if isinstance(role_or_user, discord.Role):
            async with self.config.guild(ctx.guild).ignore.roles() as ignored:
                if role_or_user.id in ignored:
                    ignored.remove(role_or_user.id)
        elif isinstance(role_or_user, discord.Member):
            async with self.config.guild(ctx.guild).ignore.users() as ignored:
                if role_or_user.id in ignored:
                    ignored.remove(role_or_user.id)
        else:
            # Shouldn't happen
            return await ctx.send("Error: input not a role or user.")

        return await ctx.tick()

    @_template_posts.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View TemplatePosts settings for this server."""

        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="TemplatePosts Settings", color=await ctx.embed_color(), description=f"""
        **Toggle:** {settings['toggle']}
        **Send DM:** {settings['dm']}
        **Ignored Roles:** {humanize_list([ctx.guild.get_role(r).mention for r in settings['ignore']['roles']]) if settings['ignore']['roles'] else None}
        **Ignored Users:** {humanize_list([ctx.guild.get_member(u).mention for u in settings['ignore']['users']]) if settings['ignore']['users'] else None}
        {"**Templates:** None" if not settings['templates'] else ""}
        """)

        for name, template in settings['templates'].items():
            embed.add_field(name=f"Template `{name}`", inline=False, value=f"""**Toggle:** {template['toggle']}
            **Channel:** {ctx.guild.get_channel(template['channel']).mention}
            **DM Message:** {template['message'] if template['message'] else None}
            **Fields:** {humanize_list([f'`{f}`' for f in template['fields']])}
            """)

        return await ctx.send(embed=embed)

from redbot.core import commands, Config
import discord


class PrivateRooms(commands.Cog):
    """Automatic Private VCs with Lobby"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "toggle": False,
            "systems": {},
        }
        self.config.register_guild(**default_guild)
        self.bot.loop.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for g in all_guilds.keys():
            async with self.config.guild_from_id(g).all() as guild:
                for sys in guild['systems'].values():
                    for a in sys['active']:
                        try:
                            vc = self.bot.get_channel(a[0])
                            if not vc.members:
                                await vc.delete(reason="PrivateRooms: unused VC after cog load")
                                sys['active'].remove(a)
                        except (AttributeError, discord.NotFound, discord.HTTPException, discord.Forbidden, discord.InvalidData):
                            sys['active'].remove(a)

    @commands.Cog.listener("on_voice_state_update")
    async def _voice_listener(self, member: discord.Member, before, after):

        if (
            not await self.config.guild(member.guild).toggle() or  # PrivateRooms toggled off
            member.bot or  # Member is a bot
            await self.bot.cog_disabled_in_guild(self, member.guild)  # Cog disabled in guild
        ):
            return

        leftroom = False
        joinedroom = False

        # Moved channels
        if before.channel and after.channel:
            async with self.config.guild(member.guild).systems() as systems:
                for sys in systems.values():
                    if not sys['toggle']:
                        continue

                    active_vcs = [x[0] for x in sys['active']]

                    # Member joined an active PrivateRoom
                    if sys['log_channel'] and sys['lobby'] == before.channel.id and after.channel.id in active_vcs:
                        await member.guild.get_channel(sys['log_channel']).send(f'{member.mention} joined `{after.channel.name}`')

                    # Member left a PrivateRoom
                    if before.channel.id in active_vcs:
                        leftroom = True

                    # Member went into the origin channel
                    if sys['origin'] == after.channel.id:
                        joinedroom = True

                    if leftroom and joinedroom:
                        break

        # Left a channel
        if (before.channel and not after.channel) or leftroom:
            async with self.config.guild(member.guild).systems() as systems:
                for sys in systems.values():
                    # Skip system if not toggled on
                    if not sys['toggle']:
                        continue

                    for a in sys['active']:
                        if not a[0] == before.channel.id:
                            continue

                        # Owner left channel
                        if a[1] == member.id:
                            remaining = None
                            for m in before.channel.members:
                                if not m.bot and m.id != member.id:
                                    remaining = m
                                    break

                            lobby = member.guild.get_channel(sys['lobby'])
                            new_overwrites_lobby = lobby.overwrites
                            new_overwrites_before = before.channel.overwrites
                            # Reassign to another user
                            if remaining:
                                a[1] = remaining.id
                                new_overwrites_before.pop(member)
                                new_overwrites_before.update({remaining: discord.PermissionOverwrite(move_members=True, view_channel=True, connect=True)})
                                await before.channel.edit(
                                    name=sys['channel_name'].replace("{creator}", remaining.display_name),
                                    overwrites=new_overwrites_before,
                                    reason=f"PrivateRooms: {member.display_name} left their VC, ownership transferred to {remaining.id}"
                                )
                                new_overwrites_lobby.pop(member)
                                new_overwrites_lobby.update({remaining: discord.PermissionOverwrite(move_members=True)})
                                await lobby.edit(
                                    overwrites=new_overwrites_lobby,
                                    reason=f"PrivateRooms: {member.display_name} has left their VC, ownership transferred to {remaining.id}"
                                )
                                if sys['log_channel']:
                                    await member.guild.get_channel(sys['log_channel']).send(f'{member.mention} left `{before.channel.name}`, channel reassigned to {remaining.mention}')

                            # Remove channel
                            else:
                                sys['active'].remove(a)
                                try:
                                    await before.channel.delete(reason="PrivateRooms: all users have left")
                                except discord.Forbidden:
                                    pass
                                new_overwrites_lobby.pop(member)
                                await lobby.edit(
                                    overwrites=new_overwrites_lobby,
                                    reason=f"PrivateRooms: {member.display_name}'s private VC has been deleted"
                                )
                                if sys['log_channel']:
                                    await member.guild.get_channel(sys['log_channel']).send(f'{member.mention} left `{before.channel.name}`, channel removed')

                            break

                        # Other user left channel
                        elif sys['log_channel']:
                            await member.guild.get_channel(sys['log_channel']).send(f'{member.mention} left `{before.channel.name}`')
                            break

        # Joined a channel
        if (not before.channel and after.channel) or joinedroom:
            async with self.config.guild(member.guild).systems() as systems:
                for sys in systems.values():

                    # Joined an Origin channel of a system that is toggled on
                    if sys['toggle'] and sys['origin'] == after.channel.id:
                        # Create their private VC
                        private_vc = await member.guild.create_voice_channel(
                            name=sys['channel_name'].replace("{creator}", member.display_name),
                            category=after.channel.category,
                            bitrate=min(sys['bitrate']*1000, member.guild.bitrate_limit),
                            reason=f"PrivateRooms: created by {member.display_name}",
                            overwrites={
                                member: discord.PermissionOverwrite(move_members=True, view_channel=True, connect=True),
                                member.guild.default_role: discord.PermissionOverwrite(connect=False),
                                member.guild.me: discord.PermissionOverwrite(connect=True)
                            }
                        )

                        # Move creator to their private room
                        await member.move_to(private_vc, reason="PrivateRooms: is VC creator")

                        # Edit Lobby channel to have permission overwrite
                        lobby = member.guild.get_channel(sys['lobby'])
                        new_overwrites = lobby.overwrites
                        new_overwrites[member] = discord.PermissionOverwrite(move_members=True)
                        await lobby.edit(
                            overwrites=new_overwrites,
                            reason=f"PrivateRooms: {member.display_name} has created a new private VC"
                        )

                        # If log channel set, then send logs
                        if sys['log_channel']:
                            await member.guild.get_channel(sys['log_channel']).send(f'{member.mention} created `{private_vc.name}`')

                        # Add to active list
                        sys['active'].append((private_vc.id, member.id))

                        break

        return

    @commands.guild_only()
    @commands.admin()
    @commands.group(name="privaterooms")
    async def _privaterooms(self, ctx: commands.Context):
        """Set Up Private VC Systems"""

    @_privaterooms.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle PrivateRooms in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_privaterooms.command(name="add")
    async def _add(self, ctx: commands.Context, system_name: str, origin_channel: discord.VoiceChannel, lobby_channel: discord.VoiceChannel, default_bitrate_in_kbps: int, *, channel_name_template: str):
        """
        Add a new PrivateRooms system in this server.

        For the `channel_name_template`, enter a string, with `{creator}` contained if you want it to be replaced with the VC creator's display name.
        """

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name in systems.keys():
                return await ctx.send("There is already a PrivateRooms system with that name!")

            systems[system_name] = {
                "toggle": True,
                "origin": origin_channel.id,
                "lobby": lobby_channel.id,
                "bitrate": default_bitrate_in_kbps,
                "channel_name": channel_name_template,
                "log_channel": None,
                "active": []
            }

        return await ctx.send(f'A new PrivateRooms system with origin channel `{origin_channel.name}` and lobby `{lobby_channel.name}` has been created and toggled on. If you would like to toggle it or set a log channel, please use `{ctx.clean_prefix}privaterooms edit logchannel {system_name}`.')

    @_privaterooms.group(name="edit")
    async def _edit(self, ctx: commands.Context):
        """Edit a PrivateRooms System"""

    @_edit.command(name="toggle")
    async def _edit_toggle(self, ctx: commands.Context, system_name: str, true_or_false: bool):
        """Toggle a PrivateRooms system in this server."""
        async with self.config.guild(ctx.guild).systems() as systems:
            systems[system_name]["toggle"] = true_or_false
        return await ctx.tick()

    @_edit.command(name="origin")
    async def _edit_origin(self, ctx: commands.Context, system_name: str, origin_channel: discord.VoiceChannel):
        """Edit the Origin channel for a PrivateRooms system in this server."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            systems[system_name]["origin"] = origin_channel.id

        return await ctx.tick()

    @_edit.command(name="lobby")
    async def _edit_lobby(self, ctx: commands.Context, system_name: str, lobby_channel: discord.VoiceChannel):
        """Edit the Lobby channel for a PrivateRooms system in this server."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            systems[system_name]["lobby"] = lobby_channel.id

        return await ctx.tick()

    @_edit.command(name="bitrate")
    async def _edit_bitrate(self, ctx: commands.Context, system_name: str, bitrate_in_kbps: int):
        """Edit the new VC bitrate (in kbps) for a PrivateRooms system in this server."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            systems[system_name]["bitrate"] = bitrate_in_kbps

        return await ctx.tick()

    @_edit.command(name="name")
    async def _edit_name(self, ctx: commands.Context, system_name: str, *, channel_name_template: str):
        """
        Edit the Lobby channel for a PrivateRooms system in this server.

        Enter a string, with `{creator}` contained if you want it to be replaced with the VC creator's display name.
        """

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            systems[system_name]["channel_name"] = channel_name_template

        return await ctx.tick()

    @_edit.command(name="logchannel")
    async def _edit_log_channel(self, ctx: commands.Context, system_name: str, channel: discord.TextChannel = None):
        """Edit the log channel for a PrivateRooms system in this server (leave blank to set to None)."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            if channel:
                systems[system_name]["log_channel"] = channel.id
            else:
                systems[system_name]["log_channel"] = None

        return await ctx.tick()

    @_privaterooms.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, system_name: str, enter_true_to_confirm: bool):
        """Remove a PrivateRooms system in this server."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            del systems[system_name]

        return await ctx.send(f"The PrivateRooms system `{system_name}` was removed.")

    @_privaterooms.command(name="clearactive")
    async def _clear_active(self, ctx: commands.Context, system_name: str, enter_true_to_confirm: bool):
        """Clears the cache of current active PrivateRooms."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PrivateRooms system found with that name!")

            systems[system_name]["active"] = []

        return await ctx.send(f"The active rooms in `{system_name}` were cleared.")

    @_privaterooms.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the PrivateRooms settings in this server."""

        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="PrivateRooms Settings", color=await ctx.embed_color(), description=f"""
        **Server Toggle:** {settings['toggle']}
        {"**Systems:** None" if not settings['systems'] else ""}
        """)

        for name, system in settings['systems'].items():
            embed.add_field(name=f"System `{name}`", inline=False, value=f"""
            **Toggle:** {system['toggle']}
            **Origin:** {ctx.guild.get_channel(system['origin']).name}
            **Lobby:** {ctx.guild.get_channel(system['lobby']).name}
            **BitRate:** {system['bitrate']} kbps
            **Name Template:** {system['channel_name']}
            **Log Channel:** {ctx.guild.get_channel(system['log_channel']).mention if system['log_channel'] else None}
            """)

        return await ctx.send(embed=embed)

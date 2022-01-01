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

from datetime import datetime

import discord
from redbot.core import commands, Config


class PublicRooms(commands.Cog):
    """
    Automatic Public VC Creation

    Public VCs that are created automatically, with customizable channel naming templates and support for multiple systems.
    """

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
            if guild := self.bot.get_guild(g):
                async with self.config.guild_from_id(g).all() as guild_settings:
                    for sys in guild_settings['systems'].values():
                        for a in sys['active']:
                            vc = guild.get_channel(a[0])
                            if not vc or not vc.members:
                                sys['active'].remove(a)
                            if vc and not vc.members and vc.permissions_for(guild.me).manage_channels:
                                await vc.delete(reason="PublicRooms: unused VC found on cog load")

    @commands.Cog.listener("on_voice_state_update")
    async def _voice_listener(self, member: discord.Member, before, after):

        if (
            not await self.config.guild(member.guild).toggle() or  # PublicRooms toggled off
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

                    active = [x[0] for x in sys['active']]

                    # Member joined an active PublicRoom
                    log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                    if log_channel and before.channel.id not in active and after.channel.id in active:
                        await self._send_log(
                            channel=log_channel,
                            text=f"{member.mention} joined `{after.channel.name}`",
                            color=discord.Color.magenta(),
                            embed_links=embed_links
                        )

                    # Member left a PublicRoom
                    if before.channel.id in active and before.channel.id != after.channel.id:
                        leftroom = True

                    # Member went into the origin channel
                    if sys['origin'] == after.channel.id != before.channel.id:
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

                        # Everyone left channel
                        if not before.channel.members:
                            sys['active'].remove(a)
                            if before.channel.permissions_for(member.guild.me).manage_channels:
                                await before.channel.delete(reason="PublicRooms: all users have left")
                            else:
                                return
                            log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                            if log_channel:
                                await self._send_log(
                                    channel=log_channel,
                                    text=f"{member.mention} left `{before.channel.name}`, channel removed",
                                    color=discord.Color.dark_teal(),
                                    embed_links=embed_links,
                                )
                            break

                        # Member with custom channel name left
                        if sys['overrides'].get(str(member.id)) == before.channel.name :
                            # Find correct position of new channel
                            no_created = False
                            no_missing = False
                            all_nums = [x[1] for x in sys['active'] if x[1] != 0]
                            try:
                                num = list(set(range(1, max(all_nums) + 1)) - set(all_nums))[0]
                                for i in sorted(sys['active'], key=lambda x: x[1]):
                                    if i[1] > num:
                                        ch = i[0]
                                        break
                                position = member.guild.get_channel(ch).position - 1
                            except IndexError:
                                num = max(all_nums) + 1
                                no_missing = True
                            except ValueError:
                                no_created = True

                            if before.channel.permissions_for(member.guild.me).manage_channels:
                                if no_created or no_missing:
                                    if no_created:
                                        num = 1
                                    public_vc = await before.channel.edit(
                                        name=sys['channel_name'].replace("{num}", str(num)),
                                        reason=f"PublicRooms: {member.display_name} left room with custom name",
                                    )
                                else:
                                    public_vc = await before.channel.edit(
                                        name=sys['channel_name'].replace("{num}", str(num)),
                                        position=position,
                                        reason=f"PublicRooms: {member.display_name} left room with custom name",
                                    )
                            else:
                                return

                            log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                            if log_channel:
                                await self._send_log(
                                    channel=log_channel,
                                    text=f"{member.mention} left `{before.channel.name}`, renamed to {public_vc.name}",
                                    color=discord.Color.teal(),
                                    embed_links=embed_links,
                                )

                            break

                        # Log user leaving
                        log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                        if log_channel:
                            await self._send_log(
                                channel=log_channel,
                                text=f"{member.mention} left `{before.channel.name}`",
                                color=discord.Color.magenta(),
                                embed_links=embed_links,
                            )

                        break

        # Joined a channel
        if (not before.channel and after.channel) or joinedroom:
            async with self.config.guild(member.guild).systems() as systems:
                for sys in systems.values():

                    # Joined an Origin channel of a system that is toggled on
                    if sys['toggle'] and sys['origin'] == after.channel.id:
                        # Create the new VC
                        if not after.channel.category.permissions_for(member.guild.me).manage_channels:
                            return
                        channel_name = sys['overrides'].get(str(member.id))
                        if channel_name:
                            num = 0
                            public_vc = await member.guild.create_voice_channel(
                                name=channel_name,
                                category=after.channel.category,
                                position=after.channel.position+1,
                                bitrate=min(sys['bitrate'] * 1000, member.guild.bitrate_limit),
                                reason=f"PublicRooms: created by {member.display_name}",
                            )
                        else:
                            # Find correct position of new channel
                            no_created = False
                            no_missing = False
                            all_nums = [x[1] for x in sys['active']]
                            try:
                                num = list(set(range(1, max(all_nums) + 1)) - set(all_nums))[0]
                                for i in sorted(sys['active'], key=lambda x: x[1]):
                                    if i[1] > num:
                                        ch = i[0]
                                        break
                                position = member.guild.get_channel(ch).position - 1
                            except IndexError:
                                num = max(all_nums) + 1
                                no_missing = True
                            except ValueError:
                                no_created = True

                            if no_created or no_missing:
                                if no_created:
                                    num = 1
                                public_vc = await member.guild.create_voice_channel(
                                    name=sys['channel_name'].replace("{num}", str(num)),
                                    category=after.channel.category,
                                    bitrate=min(sys['bitrate']*1000, member.guild.bitrate_limit),
                                    reason=f"PublicRooms: created by {member.display_name}",
                                )
                            else:
                                public_vc = await member.guild.create_voice_channel(
                                    name=sys['channel_name'].replace("{num}", str(num)),
                                    category=after.channel.category,
                                    position=position,
                                    bitrate=min(sys['bitrate'] * 1000, member.guild.bitrate_limit),
                                    reason=f"PublicRooms: created by {member.display_name}",
                                )

                        # Move creator to their new room
                        if not (after.channel.permissions_for(member.guild.me).move_members and public_vc.permissions_for(member.guild.me).move_members):
                            return
                        await member.move_to(public_vc, reason="PublicRooms: is VC creator")

                        # If log channel set, then send logs
                        log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                        if log_channel:
                            await self._send_log(
                                channel=log_channel,
                                text=f"{member.mention} created `{public_vc.name}`",
                                color=discord.Color.teal(),
                                embed_links=embed_links,
                            )

                        # Add to active list
                        sys['active'].append((public_vc.id, num))

                        break

                    # Member joined an active PublicRoom
                    elif sys['toggle'] and sys['log_channel'] and after.channel.id in [x[0] for x in sys['active']]:
                        log_channel, embed_links = await self._get_log(sys['log_channel'], member.guild)
                        if log_channel:
                            await self._send_log(
                                channel=log_channel,
                                text=f"{member.mention} joined `{after.channel.name}`",
                                color=discord.Color.magenta(),
                                embed_links=embed_links,
                            )

    @staticmethod
    async def _get_log(channel_id, guild: discord.Guild):
        log_channel, embed_links = None, False
        if channel_id:
            log_channel = guild.get_channel(channel_id)
            if not log_channel or not log_channel.permissions_for(guild.me).send_messages:
                log_channel = None
            if log_channel and log_channel.permissions_for(guild.me).embed_links:
                embed_links = True
        return log_channel, embed_links

    @staticmethod
    async def _send_log(channel: discord.TextChannel, text: str, color: discord.Color, embed_links: bool):
        if embed_links:
            return await channel.send(embed=discord.Embed(
                timestamp=datetime.utcnow(),
                color=color,
                description=text
            ))
        else:
            return await channel.send(
                text,
                allowed_mentions=discord.AllowedMentions.none()
            )

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="publicrooms")
    async def _publicrooms(self, ctx: commands.Context):
        """Set Up Public VC Systems"""

    @_publicrooms.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle PublicRooms in this server."""
        await self.config.guild(ctx.guild).toggle.set(true_or_false)
        return await ctx.tick()

    @_publicrooms.command(name="add")
    async def _add(self, ctx: commands.Context, system_name: str, origin_channel: discord.VoiceChannel, default_bitrate_in_kbps: int, *, channel_name_template: str):
        """
        Add a new PublicRooms system in this server.

        For the `channel_name_template`, enter a string, with `{num}` contained if you want it to be replaced with the number of active VCs.
        """

        if origin_channel.category and not origin_channel.category.permissions_for(ctx.guild.me).manage_channels:
            return await ctx.send("I don't have the `Manage Channels` permission in that category!")
        elif not origin_channel.category and not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("I don't have the `Manage Channels` permission in this server!")

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name in systems.keys():
                return await ctx.send("There is already a PublicRooms system with that name!")

            systems[system_name] = {
                "toggle": True,
                "origin": origin_channel.id,
                "bitrate": default_bitrate_in_kbps,
                "channel_name": channel_name_template,
                "log_channel": None,
                "active": [],
                "overrides": {}
            }

        return await ctx.send(f'A new PublicRooms system with origin channel `{origin_channel.name}` has been created and toggled on. If you would like to toggle it or set a log channel, please use `{ctx.clean_prefix}publicrooms edit logchannel {system_name}`.')

    @_publicrooms.group(name="edit")
    async def _edit(self, ctx: commands.Context):
        """Edit a PublicRooms System"""

    @_edit.command(name="toggle")
    async def _edit_toggle(self, ctx: commands.Context, system_name: str, true_or_false: bool):
        """Toggle a PublicRooms system in this server."""
        async with self.config.guild(ctx.guild).systems() as systems:
            systems[system_name]["toggle"] = true_or_false
        return await ctx.tick()

    @_edit.command(name="origin")
    async def _edit_origin(self, ctx: commands.Context, system_name: str, origin_channel: discord.VoiceChannel):
        """Edit the Origin channel for a PublicRooms system in this server."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            systems[system_name]["origin"] = origin_channel.id

        return await ctx.tick()

    @_edit.command(name="bitrate")
    async def _edit_bitrate(self, ctx: commands.Context, system_name: str, bitrate_in_kbps: int):
        """Edit the new VC bitrate (in kbps) for a PublicRooms system in this server."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            systems[system_name]["bitrate"] = bitrate_in_kbps

        return await ctx.tick()

    @_edit.command(name="name")
    async def _edit_name(self, ctx: commands.Context, system_name: str, *, channel_name_template: str):
        """
        Edit the channel name template for a PublicRooms system in this server.

        Enter a string, with `{num}` contained if you want it to be replaced with the number of active VCs.
        """

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            systems[system_name]["channel_name"] = channel_name_template

        return await ctx.tick()

    @_edit.command(name="logchannel")
    async def _edit_log_channel(self, ctx: commands.Context, system_name: str, channel: discord.TextChannel = None):
        """Edit the log channel for a PublicRooms system in this server (leave blank to set to None)."""

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            if channel:
                if not channel.permissions_for(ctx.guild.me).send_messages:
                    return await ctx.send(f"I cannot send messages to {channel.mention}!")
                systems[system_name]["log_channel"] = channel.id
            else:
                systems[system_name]["log_channel"] = None

        return await ctx.tick()

    @_publicrooms.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx: commands.Context, system_name: str, enter_true_to_confirm: bool):
        """Remove a PublicRooms system in this server."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            del systems[system_name]

        return await ctx.send(f"The PublicRooms system `{system_name}` was removed.")

    @_publicrooms.command(name="clearactive")
    async def _clear_active(self, ctx: commands.Context, system_name: str, enter_true_to_confirm: bool):
        """Clears the cache of current active PublicRooms."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            systems[system_name]["active"] = []

        return await ctx.send(f"The active rooms in `{system_name}` were cleared.")

    @_edit.group(name="custom")
    async def _custom(self, ctx: commands.Context):
        """Custom Channel Names for Specific Members"""

    @_custom.command(name="add")
    async def _custom_add(self, ctx: commands.Context, system_name: str, member: discord.Member, *, channel_name: str):
        """Add a custom channel name override for a specific member."""
        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            systems[system_name]["overrides"][member.id] = channel_name
        return await ctx.tick()

    @_custom.command(name="remove", aliases=["delete"])
    async def _custom_remove(self, ctx: commands.Context, system_name: str, member: discord.Member):
        """Remove a custom channel name override for a specific member."""
        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            try:
                del systems[system_name]["overrides"][str(member.id)]
            except KeyError:
                return await ctx.send("This member did not have a custom channel name override!")
        return await ctx.tick()

    @_custom.command(name="list")
    async def _custom_list(self, ctx: commands.Context, system_name: str):
        """List the custom channel name overrides for a PublicRooms system."""
        overrides = ""
        async with self.config.guild(ctx.guild).systems() as systems:
            if system_name not in systems.keys():
                return await ctx.send("There was no PublicRooms system found with that name!")

            for user, name in systems[system_name]["overrides"].items():
                overrides += f"{(await self.bot.get_or_fetch_member(ctx.guild, int(user))).mention}: {name}\n"
        if not overrides:
            return await ctx.send("No custom channel name overrides found for this system.")
        return await ctx.send(overrides)

    @commands.bot_has_permissions(embed_links=True)
    @_publicrooms.command(name="view")
    async def _view(self, ctx: commands.Context):
        """View the PublicRooms settings in this server."""

        settings = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="PublicRooms Settings", color=await ctx.embed_color(), description=f"""
        **Server Toggle:** {settings['toggle']}
        {"**Systems:** None" if not settings['systems'] else ""}
        """)

        for name, system in settings['systems'].items():
            origin, log = None, None
            if ori := ctx.guild.get_channel(system['origin']):
                origin = ori.name
            if system['log_channel'] and (glo := ctx.guild.get_channel(system['log_channel'])):
                log = glo.mention

            embed.add_field(name=f"System `{name}`", inline=False, value=f"""
            **Toggle:** {system['toggle']}
            **Origin:** {origin}
            **BitRate:** {system['bitrate']} kbps
            **Name Template:** {system['channel_name']}
            **Log Channel:** {log}
            """)

        return await ctx.send(embed=embed)

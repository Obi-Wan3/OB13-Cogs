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

import os
import asyncio
import shutil
import typing
import contextlib

from io import BytesIO
from zipfile import ZipFile
from zipstream.aiozipstream import AioZipStream

import discord
from redbot.core import commands, data_manager

# Error messages
TIME_OUT = "The request timed out or we are being ratelimited, please try again after a few moments."
INVOKE_ERROR = "Something went wrong while adding the emoji(s). Has the limit been reached?"
HTTP_EXCEPTION = "Something went wrong while adding the emoji(s): the source file may be too big or the limit may have been reached."
FILE_SIZE = "Unfortunately, it seems the attachment was too large to be sent."
SAME_SERVER_ONLY = "I can only edit emojis from this server!"
ROLE_HIERARCHY = "I cannot perform this action due to the Discord role hierarchy!"


class EmojiTools(commands.Cog):
    """Tools for Managing Custom Emojis"""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _ext(e: typing.Union[discord.Emoji, discord.PartialEmoji]):
        return ".gif" if e.animated else ".png"

    @staticmethod
    async def _convert_emoji(ctx: commands.Context, emoji: str, partial_emoji: bool = True):
        try:
            if partial_emoji:
                return await commands.PartialEmojiConverter().convert(ctx=ctx, argument=emoji)
            return await commands.EmojiConverter().convert(ctx=ctx, argument=emoji)
        except commands.BadArgument:
            raise commands.UserFeedbackCheckFailure(f"Invalid emoji: {emoji}")

    @commands.guild_only()
    @commands.admin_or_permissions(manage_emojis=True)
    @commands.group(name="emojitools")
    async def _emojitools(self, ctx: commands.Context):
        """
        Various tools for managing custom emojis in servers.

        `[p]emojitools add` has various tools to add emojis to the current server.
        `[p]emojitools delete` lets you remove emojis from the server.
        `[p]emojitools tozip` returns an instant `.zip` archive of emojis (w/o saving a folder permanently).
        `[p]emojitools save` allows you to save emojis to folders **in the cog data path**: this requires storage!
        """

    @commands.bot_has_permissions(embed_links=True)
    @_emojitools.command(name="info")
    async def _info(self, ctx: commands.Context, emoji: discord.Emoji):
        """Get info about a custom emoji from this server."""
        embed = discord.Embed(
            description=f"Emoji Information for {emoji}",
            color=await ctx.embed_color()
        )
        embed.add_field(
            name="Name",
            value=f"{emoji.name}"
        )
        embed.add_field(
            name="Emoji ID",
            value=f"{emoji.id}"
        )
        embed.add_field(
            name="Animated",
            value=f"{emoji.animated}"
        )
        embed.add_field(
            name="URL",
            value=f"[Image Link]({emoji.url})"
        )
        embed.add_field(
            name="Creation (UTC)",
            value=f"{str(emoji.created_at)[:19]}"
        )
        if ctx.guild.me.guild_permissions.manage_emojis:
            with contextlib.suppress(discord.HTTPException):
                e: discord.Emoji = await ctx.guild.fetch_emoji(emoji.id)
                embed.add_field(
                    name="Author",
                    value=f"{e.user.mention if e.user else 'Unknown'}"
                )
        embed.add_field(
            name="Roles Allowed",
            value=f"{emoji.roles or 'Everyone'}"
        )
        return await ctx.send(embed=embed)

    @commands.admin_or_permissions(administrator=True)
    @_emojitools.group(name="save")
    async def _save(self, ctx: commands.Context):
        """
        Save Custom Emojis to Folders

        **IMPORTANT**: this **will** save folders to the cog data path, requiring storage in the machine the bot is hosted on.
        The folders will be accessible to admin across all servers with access to this cog.
        The other `EmojiTools` features that do **NOT** require storage, so disable this command group if you wish.
        For large public bots, it is highly recommended to restrict usage of or disable this command group.
        """

    async def _maybe_create_folder(self, ctx: commands.Context, folder_name: str):
        folder_path = os.path.join(f'{data_manager.cog_data_path(self)}', f'{folder_name}')
        try:
            os.mkdir(folder_path)
        except OSError:
            await ctx.send("The emojis will be added to the existing folder with this name.")
        return folder_path

    @commands.cooldown(rate=1, per=15)
    @_save.command(name="emojis", require_var_positional=True)
    async def _emojis(self, ctx: commands.Context, folder_name: str, *emojis: str):
        """Save to a folder the specified custom emojis (can be from any server)."""

        async with ctx.typing():
            folder_path = await self._maybe_create_folder(ctx, folder_name)
            for e in emojis:
                em = await self._convert_emoji(ctx, e)
                await em.url.save(os.path.join(folder_path, f"{em.name}{self._ext(em)}"))

        return await ctx.send(f"{len(emojis)} emojis were saved to `{folder_name}`.")

    @commands.cooldown(rate=1, per=60)
    @_save.command(name="server")
    async def _server(self, ctx: commands.Context, folder_name: str = None):
        """Save to a folder all custom emojis from this server (folder name defaults to server name)."""

        async with ctx.typing():
            folder_path = await self._maybe_create_folder(ctx, folder_name or ctx.guild.name)
            for e in ctx.guild.emojis:
                await e.url.save(os.path.join(folder_path, f"{e.name}{self._ext(e)}"))

        return await ctx.send(f"{len(ctx.guild.emojis)} emojis were saved to `{folder_name or ctx.guild.name}`.")

    @_save.command(name="folders")
    async def _folders(self, ctx: commands.Context):
        """List all your saved EmojiTools folders."""

        dir_string = ""
        for ind, d in enumerate(sorted(os.listdir(f"{data_manager.cog_data_path(self)}"))):
            if os.path.isdir(os.path.join(f"{data_manager.cog_data_path(self)}", d)):
                dir_string += f"{ind}. {d}\n"

        return await ctx.maybe_send_embed(dir_string or f"You have no EmojiTools folders yet. Save emojis with `{ctx.clean_prefix}emojitools save`!")

    @commands.cooldown(rate=1, per=60)
    @_save.command(name="remove")
    async def _remove(self, ctx: commands.Context, folder_number: int):
        """Remove an EmojiTools folder."""

        dirs = sorted(os.listdir(f"{data_manager.cog_data_path(self)}"))
        try:
            to_remove = dirs[folder_number]
        except IndexError:
            return await ctx.send("Invalid folder number.")

        await self.bot.loop.run_in_executor(None, lambda: shutil.rmtree((os.path.join(f"{data_manager.cog_data_path(self)}", f"{to_remove}"))))
        return await ctx.send(f"`{to_remove}` has been removed.")

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(rate=1, per=30)
    @_save.command(name="getzip")
    async def _get_zip(self, ctx: commands.Context, folder_number: int):
        """Zip and upload an EmojiTools folder."""

        async with ctx.typing():
            items = sorted(os.listdir(f"{data_manager.cog_data_path(self)}"))

            # Clean up .zips from previous code if present
            for i in items:
                if i.endswith(".zip"):
                    await self.bot.loop.run_in_executor(None, lambda: os.remove(os.path.join(f"{data_manager.cog_data_path(self)}", f"{i}")))

            try:
                folder_to_zip = items[folder_number]
            except IndexError:
                return await ctx.send("Invalid folder number.")

            zip_path = os.path.join(f"{data_manager.cog_data_path(self)}", f"{folder_to_zip}")

            files_list = []
            for root, dirs, files in os.walk(zip_path):
                for file in files:
                    files_list.append({"file": os.path.join(root, file)})

            stream = AioZipStream(files_list, chunksize=32768)
            with BytesIO() as z:
                async for chunk in stream.stream():
                    z.write(chunk)
                z.seek(0)
                zip_file: discord.File = discord.File(z, filename=f"{folder_to_zip}.zip")

        try:
            return await ctx.send(file=zip_file)
        except discord.HTTPException:
            return await ctx.send(FILE_SIZE)

    @commands.bot_has_permissions(manage_emojis=True)
    @_emojitools.group(name="delete", aliases=["remove"])
    async def _delete(self, ctx: commands.Context):
        """Delete Server Custom Emojis"""

    @commands.cooldown(rate=1, per=15)
    @_delete.command(name="emojis", aliases=["emoji"], require_var_positional=True)
    async def _delete_emojis(self, ctx: commands.Context, *emoji_names: typing.Union[discord.Emoji, str]):
        """Delete custom emojis from the server."""
        async with ctx.typing():
            for e in emoji_names:
                if isinstance(e, str):
                    e: discord.Emoji = await self._convert_emoji(ctx, e, partial_emoji=False)
                elif e.guild_id != ctx.guild.id:
                    return await ctx.send(f"The following emoji is not in this server: {e}")
                await e.delete(reason=f"EmojiTools: deleted by {ctx.author}")
        return await ctx.send(f"The following emojis have been removed from this server: `{'`, `'.join([str(e) for e in emoji_names])}`")

    @commands.cooldown(rate=1, per=60)
    @_delete.command(name="all")
    async def _delete_all(self, ctx: commands.Context, enter_true_to_confirm: bool):
        """Delete all specific custom emojis from the server."""

        if not enter_true_to_confirm:
            return await ctx.send("Please provide `true` as the parameter to confirm.")

        async with ctx.typing():
            counter = 0
            for e in ctx.guild.emojis:
                await e.delete()
                counter += 1

        return await ctx.send(f"All {counter} custom emojis have been removed from this server.")

    @commands.bot_has_permissions(manage_emojis=True)
    @_emojitools.group(name="add")
    async def _add(self, ctx: commands.Context):
        """Add Custom Emojis to Server"""

    @commands.cooldown(rate=1, per=15)
    @_add.command(name="emoji")
    async def _add_emoji(self, ctx: commands.Context, emoji: discord.PartialEmoji, name: str = None):
        """Add an emoji to this server (leave `name` blank to use the emoji's original name)."""

        async with ctx.typing():
            try:
                final_emoji = await asyncio.wait_for(
                    ctx.guild.create_custom_emoji(
                        name=name or emoji.name,
                        image=await emoji.url.read(),
                        reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                    ),
                    timeout=10
                )
            except asyncio.TimeoutError:
                return await ctx.send(TIME_OUT)
            except commands.CommandInvokeError:
                return await ctx.send(INVOKE_ERROR)
            except discord.HTTPException:
                return await ctx.send(HTTP_EXCEPTION)

        return await ctx.send(f"{final_emoji} has been added to this server!")

    @commands.cooldown(rate=1, per=30)
    @_add.command(name="emojis", require_var_positional=True)
    async def _add_emojis(self, ctx: commands.Context, *emojis: str):
        """Add some emojis to this server."""

        async with ctx.typing():
            added_emojis = []
            for e in emojis:
                em = await self._convert_emoji(ctx, e)
                try:
                    fe = await asyncio.wait_for(
                        ctx.guild.create_custom_emoji(
                            name=em.name,
                            image=await em.url.read(),
                            reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                        ),
                        timeout=10
                    )
                    added_emojis.append(fe)
                except asyncio.TimeoutError:
                    return await ctx.send(TIME_OUT)
                except commands.CommandInvokeError:
                    return await ctx.send(INVOKE_ERROR)
                except discord.HTTPException:
                    return await ctx.send(HTTP_EXCEPTION)

        return await ctx.send(f"{len(added_emojis)} emojis were added to this server: {' '.join([str(e) for e in added_emojis])}")

    @commands.cooldown(rate=1, per=15)
    @_add.command(name="fromreaction")
    async def _add_from_reaction(self, ctx: commands.Context, specific_reaction: str, message: discord.Message, new_name: str = None):
        """Add an emoji to this server from a specific reaction on a message."""

        final_emoji = None
        async with ctx.typing():
            for r in message.reactions:
                if r.custom_emoji and r.emoji.name == specific_reaction:
                    try:
                        final_emoji = await asyncio.wait_for(
                            ctx.guild.create_custom_emoji(
                                name=new_name or r.emoji.name,
                                image=await r.emoji.url.read(),
                                reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                            ),
                            timeout=10
                        )
                    except asyncio.TimeoutError:
                        return await ctx.send(TIME_OUT)
                    except commands.CommandInvokeError:
                        return await ctx.send(INVOKE_ERROR)
                    except discord.HTTPException:
                        return await ctx.send(HTTP_EXCEPTION)

        if final_emoji:
            return await ctx.send(f"{final_emoji} has been added to this server!")
        else:
            return await ctx.send(f"No reaction called `{specific_reaction}` was found on that message!")

    @commands.cooldown(rate=1, per=30)
    @_add.command(name="allreactionsfrom")
    async def _add_all_reactions_from(self, ctx: commands.Context, message: discord.Message):
        """Add emojis to this server from all reactions in a message."""

        async with ctx.typing():
            added_emojis = []
            for r in message.reactions:
                if not r.custom_emoji:
                    continue
                try:
                    fe = await asyncio.wait_for(
                        ctx.guild.create_custom_emoji(
                            name=r.emoji.name,
                            image=await r.emoji.url.read(),
                            reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                        ),
                        timeout=10
                    )
                    added_emojis.append(fe)
                except asyncio.TimeoutError:
                    return await ctx.send(TIME_OUT)
                except commands.CommandInvokeError:
                    return await ctx.send(INVOKE_ERROR)
                except discord.HTTPException:
                    return await ctx.send(HTTP_EXCEPTION)

        return await ctx.send(f"{len(added_emojis)} emojis were added to this server: {' '.join([str(e) for e in added_emojis])}")

    @commands.cooldown(rate=1, per=15)
    @commands.admin_or_permissions(manage_emojis=True)
    @_add.command(name="fromimage")
    async def _add_from_image(self, ctx: commands.Context, name: str = None):
        """
        Add an emoji to this server from a provided image.

        The attached image should be in one of the following formats: `.png`, `.jpg`, or `.gif`.
        """

        async with ctx.typing():
            if len(ctx.message.attachments) > 1:
                return await ctx.send("Please only attach 1 file!")

            if len(ctx.message.attachments) < 1:
                return await ctx.send("Please attach an image!")

            if not ctx.message.attachments[0].filename.endswith((".png", ".jpg", ".gif")):
                return await ctx.send("Please make sure the uploaded image is a `.png`, `.jpg`, or `.gif` file!")

            image = await ctx.message.attachments[0].read()

            try:
                new = await asyncio.wait_for(
                    ctx.guild.create_custom_emoji(
                        name=name or ctx.message.attachments[0].filename[:-4],
                        image=image,
                        reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                    ),
                    timeout=10
                )
            except asyncio.TimeoutError:
                return await ctx.send(TIME_OUT)
            except commands.CommandInvokeError:
                return await ctx.send(INVOKE_ERROR)
            except discord.HTTPException:
                return await ctx.send("Something went wrong while adding emojis. Is the file size less than 256kb?")

        return await ctx.send(f"{new} has been added to this server!")

    @commands.cooldown(rate=1, per=60)
    @commands.admin_or_permissions(administrator=True)
    @_add.command(name="fromzip")
    async def _add_from_zip(self, ctx: commands.Context):
        """
        Add some emojis to this server from a provided .zip archive.

        The `.zip` archive should extract to a folder, which contains files in the formats `.png`, `.jpg`, or `.gif`.
        You can also use the `[p]emojitools tozip` command to get a zip archive, extract it, remove unnecessary emojis, then re-zip and upload.
        """

        async with ctx.typing():
            if len(ctx.message.attachments) > 1:
                return await ctx.send("Please only attach 1 file!")

            if len(ctx.message.attachments) < 1:
                return await ctx.send("Please attach a `.zip` archive!")

            if not ctx.message.attachments[0].filename.endswith(".zip"):
                return await ctx.send("Please make sure the uploaded file is a `.zip` archive!")

            added_emojis: list = []
            with ZipFile(BytesIO(await ctx.message.attachments[0].read())) as zip_file:

                for file_info in zip_file.infolist():

                    if not file_info.filename.endswith((".png", ".jpg", ".gif")):
                        await ctx.send(f"{file_info.filename} was not added as it is not a `.jpg`, `.png`, or `.gif` file.")
                        continue

                    image = zip_file.read(file_info)

                    try:
                        fe = await asyncio.wait_for(
                            ctx.guild.create_custom_emoji(
                                name=file_info.filename[:-4],
                                image=image,
                                reason=f"EmojiTools: emoji added by {ctx.author.name}#{ctx.author.discriminator}"
                            ),
                            timeout=10
                        )
                        added_emojis.append(fe)
                    except asyncio.TimeoutError:
                        return await ctx.send(TIME_OUT)
                    except commands.CommandInvokeError:
                        return await ctx.send(INVOKE_ERROR)
                    except discord.HTTPException:
                        return await ctx.send(HTTP_EXCEPTION)

        return await ctx.send(f"{len(added_emojis)} emojis were added to this server: {' '.join([str(e) for e in added_emojis])}")

    @commands.bot_has_permissions(manage_emojis=True)
    @_emojitools.group(name="edit")
    async def _edit(self, ctx: commands.Context):
        """Edit Custom Emojis in the Server"""

    @commands.cooldown(rate=1, per=15)
    @_edit.command(name="name")
    async def _edit_name(self, ctx: commands.Context, emoji: discord.Emoji, name: str):
        """Edit the name of a custom emoji from this server."""
        if emoji.guild_id != ctx.guild.id:
            return await ctx.send(SAME_SERVER_ONLY)
        await emoji.edit(name=name, reason=f"EmojiTools: edit requested by {ctx.author}")
        return await ctx.tick()

    @commands.cooldown(rate=1, per=15)
    @_edit.command(name="roles")
    async def _edit_roles(self, ctx: commands.Context, emoji: discord.Emoji, *roles: discord.Role):
        """Edit the roles to which the usage of a custom emoji from this server is restricted."""
        if emoji.guild_id != ctx.guild.id:
            return await ctx.send(SAME_SERVER_ONLY)
        for r in roles:
            if (r >= ctx.author.top_role and ctx.author != ctx.guild.owner) or r >= ctx.guild.me.top_role:
                return await ctx.send(ROLE_HIERARCHY)
        await emoji.edit(roles=roles, reason=f"EmojiTools: edit requested by {ctx.author}")
        return await ctx.tick()

    @commands.bot_has_permissions(attach_files=True)
    @_emojitools.group(name="tozip")
    async def _to_zip(self, ctx: commands.Context):
        """Get a `.zip` Archive of Emojis"""

    @staticmethod
    async def _generate_emoji(e):
        yield await e.url.read()

    async def _zip_emojis(self, emojis: list, file_name: str):

        emojis_list: list = []
        for e in emojis:
            emojis_list.append({
                "stream": self._generate_emoji(e),
                "name": f"{e.name}{self._ext(e)}"
            })

        stream = AioZipStream(emojis_list, chunksize=32768)
        with BytesIO() as z:
            async for chunk in stream.stream():
                z.write(chunk)
            z.seek(0)
            zip_file: discord.File = discord.File(z, filename=file_name)

        return zip_file

    @commands.cooldown(rate=1, per=30)
    @_to_zip.command(name="emojis", require_var_positional=True)
    async def _to_zip_emojis(self, ctx: commands.Context, *emojis: str):
        """
        Get a `.zip` archive of the provided emojis.

        The returned `.zip` archive can be used for the `[p]emojitools add fromzip` command.
        """

        async with ctx.typing():
            actual_emojis: list = [await self._convert_emoji(ctx, e) for e in emojis]
            file: discord.File = await self._zip_emojis(actual_emojis, "emojis.zip")

        try:
            return await ctx.send(f"{len(emojis)} emojis were saved to this `.zip` archive!", file=file)
        except discord.HTTPException:
            return await ctx.send(FILE_SIZE)

    @commands.cooldown(rate=1, per=60)
    @_to_zip.command(name="server")
    async def _to_zip_server(self, ctx: commands.Context):
        """
        Get a `.zip` archive of all custom emojis in the server.

        The returned `.zip` archive can be used for the `[p]emojitools add fromzip` command.
        """

        async with ctx.typing():
            file: discord.File = await self._zip_emojis(ctx.guild.emojis, f"{ctx.guild.name}.zip")

        try:
            return await ctx.send(f"{len(ctx.guild.emojis)} emojis were saved to this `.zip` archive!", file=file)
        except discord.HTTPException:
            return await ctx.send(FILE_SIZE)

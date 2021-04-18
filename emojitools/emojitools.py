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

import os
import asyncio
import shutil
import aiofiles
from io import BytesIO
from zipfile import ZipFile
from zipstream.aiozipstream import AioZipStream
from asynctempfile import TemporaryDirectory, NamedTemporaryFile

import discord
from redbot.core import commands, data_manager

# Error messages
TIME_OUT = "The request timed out or we are being ratelimited, please try again after a few moments."
INVOKE_ERROR = "Something went wrong while adding the emoji(s). Has the limit been reached?"
HTTP_EXCEPTION = "Something went wrong while adding the emoji(s) (the source file may be too big)."
FILE_SIZE = "Unfortunately, it seems the attachment was too large to be sent."


class EmojiTools(commands.Cog):
    """Tools for Managing Custom Emojis"""

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.admin_or_permissions(manage_emojis=True)
    @commands.group()
    async def emojitools(self, ctx: commands.Context):
        """
        Various tools for managing custom emojis in servers.

        `[p]emojitools add` has various tools to add emojis to the current server.
        `[p]emojitools delete` lets you remove emojis from the server.
        `[p]emojitools tozip` returns an instant `.zip` archive of emojis (w/o saving a folder permanently).
        `[p]emojitools save` allows you to save emojis to folders **in the cog data path**: this requires storage!
        """

    @commands.admin_or_permissions(administrator=True)
    @emojitools.group(name="save")
    async def _save(self, ctx: commands.Context):
        """
        Save Custom Emojis to Folders

        **IMPORTANT**: this **will** save folders to the cog data path, requiring storage in the machine the bot is hosted on.
        The folders will be accessible to admin across all servers with access to this cog.
        The other `EmojiTools` features that do **NOT** require storage, so disable this command group if you wish.
        For large public bots, it is highly recommended to restrict usage of or disable this command group.
        """

    @commands.cooldown(rate=1, per=5)
    @_save.command(name="emojis")
    async def _emojis(self, ctx: commands.Context, folder_name: str, *emojis: str):
        """Save to a folder the specified custom emojis (can be from any server)."""

        async with ctx.typing():
            folder_path = os.path.join(f'{data_manager.cog_data_path(self)}', f'{folder_name}')
            try:
                os.mkdir(folder_path)
            except OSError:
                await ctx.send("The emojis will be added to the existing folder with this name.")

            for e in emojis:
                try:
                    em = await commands.PartialEmojiConverter().convert(ctx=ctx, argument=e)
                except commands.BadArgument:
                    return await ctx.send(f"Invalid emoji: {e}")

                em_image = await em.url.read()
                if em.animated:
                    ext = ".gif"
                else:
                    ext = ".png"

                async with aiofiles.open(os.path.join(folder_path, f"{em.name}{ext}"), mode='wb') as f:
                    await f.write(em_image)

        return await ctx.send(f"{len(emojis)} emojis were saved to `{folder_name}`.")

    @commands.cooldown(rate=1, per=30)
    @_save.command(name="server")
    async def _server(self, ctx: commands.Context, folder_name: str = None):
        """Save to a folder all custom emojis from this server (folder name defaults to server name)."""

        async with ctx.typing():
            if folder_name is None:
                folder_name = ctx.guild.name
            folder_path = os.path.join(f'{data_manager.cog_data_path(self)}', f'{folder_name}')
            try:
                os.mkdir(folder_path)
            except OSError:
                await ctx.send("The emojis will be added to the existing folder with this name.")

            count = 0
            for e in ctx.guild.emojis:
                count += 1
                if e.animated:
                    await e.url.save(os.path.join(folder_path, f"{e.name}.gif"))
                else:
                    await e.url.save(os.path.join(folder_path, f"{e.name}.png"))

        return await ctx.send(f"{count} emojis were saved to `{folder_name}`.")

    @_save.command(name="folders")
    async def _folders(self, ctx: commands.Context):
        """List all your saved EmojiTools folders."""

        dirs = os.listdir(f"{data_manager.cog_data_path(self)}")
        dir_string = ""
        for ind, d in enumerate(sorted(dirs)):
            if os.path.isdir(os.path.join(f"{data_manager.cog_data_path(self)}", d)):
                dir_string += f"{ind}. {d}\n"

        if dir_string == "":
            dir_string = f"You have no EmojiTools folders yet. Save emojis with `{ctx.clean_prefix}emojitools`!"

        return await ctx.maybe_send_embed(dir_string)

    @commands.cooldown(rate=1, per=5)
    @_save.command(name="remove")
    async def _remove(self, ctx: commands.Context, folder_number: int):
        """Remove an EmojiTools folder."""

        dirs = sorted(os.listdir(f"{data_manager.cog_data_path(self)}"))
        try:
            to_remove = dirs[folder_number]
        except IndexError:
            return await ctx.send("Invalid folder number.")

        shutil.rmtree(os.path.join(f"{data_manager.cog_data_path(self)}", f"{to_remove}"))
        return await ctx.send(f"`{to_remove}` has been removed.")

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(rate=1, per=10)
    @_save.command(name="getzip")
    async def _getzip(self, ctx: commands.Context, folder_number: int):
        """Zip and upload an EmojiTools folder."""

        async with ctx.typing():
            dirs = sorted(os.listdir(f"{data_manager.cog_data_path(self)}"))
            for d in dirs:
                if d.endswith(".zip"):
                    os.remove(os.path.join(f"{data_manager.cog_data_path(self)}", f"{d}"))
            try:
                to_zip = dirs[folder_number]
            except IndexError:
                return await ctx.send("Invalid folder number.")

            zip_path = os.path.join(f"{data_manager.cog_data_path(self)}", f"{to_zip}")
            aiozip = AioZipStream(await self.getfiles(zip_path), chunksize=32768)
            async with aiofiles.open(zip_path+".zip", mode='wb+') as z:
                async for chunk in aiozip.stream():
                    await z.write(chunk)

            zip_file_obj = discord.File(zip_path+".zip")

        try:
            return await ctx.send(file=zip_file_obj)
        except discord.HTTPException:
            return await ctx.send(FILE_SIZE)

    @staticmethod
    async def getfiles(path):
        files_list = []
        for root, dirs, files in os.walk(path):
            for file in files:
                files_list.append({"file": os.path.join(root, file)})
        return files_list

    @commands.bot_has_permissions(manage_emojis=True)
    @emojitools.group(name="delete")
    async def _delete(self, ctx: commands.Context):
        """Delete Server Custom Emojis"""

    @commands.cooldown(rate=1, per=5)
    @_delete.command(name="emoji")
    async def _delete_emoji(self, ctx: commands.Context, emoji_name: str):
        """Delete a specific custom emoji from the server."""
        for e in ctx.guild.emojis:
            if e.name == emoji_name:
                await e.delete()
                return await ctx.send(f"The emoji `{emoji_name}` has been removed from this server!")
        return await ctx.send(f"I didn't find any emoji called `{emoji_name}`!")

    @commands.cooldown(rate=1, per=30)
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
    @emojitools.group(name="add")
    async def _add(self, ctx: commands.Context):
        """Add Custom Emojis to Server"""

    @commands.cooldown(rate=1, per=5)
    @_add.command(name="emoji")
    async def _add_emoji(self, ctx: commands.Context, emoji: discord.PartialEmoji, name: str = None):
        """Add an emoji to this server (leave `name` blank to use the emoji's original name)."""

        async with ctx.typing():
            e_image = await emoji.url.read()
            e_name = name or emoji.name
            try:
                final_emoji = await asyncio.wait_for(
                    ctx.guild.create_custom_emoji(
                        name=e_name,
                        image=e_image,
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
    @_add.command(name="emojis")
    async def _add_emojis(self, ctx: commands.Context, *emojis: str):
        """Add some emojis to this server."""

        async with ctx.typing():
            added_emojis = []
            for e in emojis:
                try:
                    em = await commands.PartialEmojiConverter().convert(ctx=ctx, argument=e)
                except commands.BadArgument:
                    return await ctx.send(f"Invalid emoji: {e}")
                em_image = await em.url.read()
                try:
                    fe = await asyncio.wait_for(
                        ctx.guild.create_custom_emoji(
                            name=em.name,
                            image=em_image,
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

    @commands.admin_or_permissions(manage_emojis=True)
    @commands.cooldown(rate=1, per=5)
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

    @commands.admin_or_permissions(administrator=True)
    @commands.cooldown(rate=1, per=60)
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

            folder_path = os.path.join(f"{data_manager.cog_data_path(self)}", f"{ctx.message.attachments[0].filename}")

            loop = asyncio.get_running_loop()
            zip_obj = BytesIO(await ctx.message.attachments[0].read())
            await loop.run_in_executor(None, lambda: self._extract_zip(zip_obj, folder_path))

            added_emojis = []
            for efile_name in os.listdir(folder_path):
                efile_path = os.path.join(folder_path, efile_name)
                if efile_name.endswith((".png", ".jpg", ".gif")):
                    async with aiofiles.open(efile_path, 'rb') as efile:
                        eimage = await efile.read()
                    try:
                        fe = await asyncio.wait_for(
                            ctx.guild.create_custom_emoji(
                                name=os.path.splitext(efile_name)[0],
                                image=eimage,
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
                else:
                    await ctx.send(f"{efile_name} was not added as it is not a `.jpg`, `.png`, or `.gif` file.")

            shutil.rmtree(folder_path)

        return await ctx.send(f"{len(added_emojis)} emojis were added to this server: {' '.join([str(e) for e in added_emojis])}")

    @staticmethod
    def _extract_zip(bfile, path):
        with ZipFile(bfile) as zfile:
            zfile.extractall(path)

    @commands.bot_has_permissions(attach_files=True)
    @emojitools.group(name="tozip")
    async def _to_zip(self, ctx: commands.Context):
        """Get a `.zip` Archive of Emojis"""

    @commands.cooldown(rate=1, per=15)
    @_to_zip.command(name="emojis")
    async def _to_zip_emojis(self, ctx: commands.Context, *emojis: str):
        """
        Get a `.zip` archive of a list of emojis.

        The returned `.zip` archive can be used for the `[p]emojitools add fromzip` command.
        """

        async with ctx.typing():
            async with TemporaryDirectory() as temp_dir:
                for e in emojis:
                    try:
                        em = await commands.PartialEmojiConverter().convert(ctx=ctx, argument=e)
                    except commands.BadArgument:
                        return await ctx.send(f"Invalid emoji: {e}")

                    if em.animated:
                        await em.url.save(os.path.join(temp_dir, f"{em.name}.gif"))
                    else:
                        await em.url.save(os.path.join(temp_dir, f"{em.name}.png"))

                aiozip = AioZipStream(await self.getfiles(temp_dir), chunksize=32768)
                async with NamedTemporaryFile('wb+') as z:
                    async for chunk in aiozip.stream():
                        await z.write(chunk)
                    await z.seek(0)
                    zip_file_obj = discord.File(z.name, filename="emojis.zip")
        try:
            return await ctx.send(f"{len(emojis)} emojis were saved to this `.zip` archive!", file=zip_file_obj)
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
            count = 0
            async with TemporaryDirectory() as temp_dir:
                for e in ctx.guild.emojis:
                    count += 1
                    if e.animated:
                        await e.url.save(os.path.join(temp_dir, f"{e.name}.gif"))
                    else:
                        await e.url.save(os.path.join(temp_dir, f"{e.name}.png"))

                aiozip = AioZipStream(await self.getfiles(temp_dir), chunksize=32768)
                async with NamedTemporaryFile('wb+') as z:
                    async for chunk in aiozip.stream():
                        await z.write(chunk)
                    await z.seek(0)
                    zip_file_obj = discord.File(z.name, filename=f"{ctx.guild.name}.zip")

        try:
            return await ctx.send(f"{count} emojis were saved to this `.zip` archive!", file=zip_file_obj)
        except discord.HTTPException:
            return await ctx.send(FILE_SIZE)

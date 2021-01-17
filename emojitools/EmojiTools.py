from redbot.core import commands, data_manager
import discord
import os
import shutil
import re
import aiohttp
import aiofiles
from zipstream.aiozipstream import AioZipStream


class EmojiTools(commands.Cog):
    """Tools for Managing Custom Emojis"""

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.admin()
    @commands.group()
    async def emojitools(self, ctx: commands.Context):
        """Various tools for managing custom emojis in servers."""

    @emojitools.group(name="save")
    async def _save(self, ctx: commands.Context):
        """Save Custom Emojis to Folders"""

    @_save.command(name="emojis")
    async def _emojis(self, ctx: commands.Context, folder_name: str, *emojis: str):
        """Save to a folder the specified custom emojis (can be from any server)."""

        with ctx.typing():
            folder_path = os.path.join(f'{data_manager.cog_data_path(self)}', f'{folder_name}')
            try:
                os.mkdir(folder_path)
            except OSError:
                return await ctx.send("A folder already exists with this name! Please remove the folder first.")

            for em in emojis:
                match = re.fullmatch(f"<(a?):(.*?):(\d*)>", em)
                if match is not None:
                    async with aiohttp.ClientSession() as session:
                        if match.group(1):
                            ext = ".gif"
                        else:
                            ext = ".png"

                        async with session.get(f"https://cdn.discordapp.com/emojis/{match.group(3)}{ext}") as resp:
                            if resp.status == 200:
                                async with aiofiles.open(os.path.join(folder_path, f"{match.group(3)}{ext}"), mode='wb') as f:
                                    await f.write(await resp.read())

                else:
                    return await ctx.send(f"Invalid emoji: {em}")

        return await ctx.send(f"{len(emojis)} emojis were saved to `{folder_name}`.")

    @_save.command(name="server")
    async def _server(self, ctx: commands.Context, folder_name: str = None):
        """Save to a folder all custom emojis from this server (folder name defaults to server name)."""

        with ctx.typing():
            if folder_name is None:
                folder_name = ctx.guild.name
            folder_path = os.path.join(f'{data_manager.cog_data_path(self)}', f'{folder_name}')
            try:
                os.mkdir(folder_path)
            except OSError:
                return await ctx.send("A folder already exists with this name! Please remove the folder first.")

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
        """List all your EmojiTools folders."""

        dirs = os.listdir(f"{data_manager.cog_data_path(self)}")
        dir_string = ""
        for ind, d in enumerate(sorted(dirs)):
            if os.path.isdir(os.path.join(f"{data_manager.cog_data_path(self)}", d)):
                dir_string += f"{ind}. {d}\n"

        if dir_string == "":
            dir_string = "You have no EmojiTools folders yet. Save emojis with `[p]emojitools`!"

        e = discord.Embed(title="EmojiTools Folders", description=dir_string, color=await ctx.embed_color())
        return await ctx.send(embed=e)

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

    @_save.command(name="getzip")
    async def _getzip(self, ctx: commands.Context, folder_number: int):
        """Zip and upload an EmojiTools folder."""

        with ctx.typing():
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

        return await ctx.send(file=zip_file_obj)

    @staticmethod
    async def getfiles(path):
        files_list = []
        for root, dirs, files in os.walk(path):
            for file in files:
                files_list.append({"file": os.path.join(root, file)})
        return files_list

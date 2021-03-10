from redbot.core import commands
import discord
import googletrans


class Translate(commands.Cog):
    """Simple translation."""

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name="translate")
    async def _translate(self, ctx: commands.Context, language, *, message):
        """Translate some text."""
        translator = googletrans.Translator()
        translated_embed = discord.Embed(title='Translation', color=discord.Color.green())
        if language.lower() in googletrans.LANGUAGES:
            language = googletrans.LANGUAGES[language.lower()]
        elif language.lower() in ("zh", "ch") or language.lower() == "chinese":
            language = "zh-cn"
        try:
            res = translator.translate(message, dest=language)
        except (ValueError, AttributeError):
            failed_embed = discord.Embed(description="Translation failed.", color=discord.Color.red())
            return await ctx.channel.send(embed=failed_embed)
        translated_embed.add_field(name=googletrans.LANGUAGES[res.src.lower()].title(), value=res.origin, inline=True)
        translated_embed.add_field(name=googletrans.LANGUAGES[res.dest.lower()].title(), value=res.text, inline=True)
        return await ctx.channel.send(embed=translated_embed)

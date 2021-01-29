from .uploadstreaks import UploadStreaks


async def setup(bot):
    bot.add_cog(UploadStreaks(bot))
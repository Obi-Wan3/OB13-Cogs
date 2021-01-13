from .github import Github


async def setup(bot):
    bot.add_cog(Github(bot))

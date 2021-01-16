from .quizrole import QuizRole


async def setup(bot):
    bot.add_cog(QuizRole(bot))
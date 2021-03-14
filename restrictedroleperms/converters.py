from redbot.core import commands


class ExplicitAll(commands.Converter):
    async def convert(self, ctx, value):
        if value.lower() == "all":
            return "all"
        raise commands.BadArgument('Input was not "all".')

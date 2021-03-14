from redbot.core import commands


# Thanks so much Flame!
class ExplicitNone(commands.Converter):
    async def convert(self, ctx, value):
        if value.lower() == "none":
            return None
        raise commands.BadArgument('Input was not "None".')


class PositiveInteger(commands.Converter):
    async def convert(self, ctx, value) -> int:
        try:
            if int(value) > 0:
                return int(value)
            raise commands.BadArgument('Input was not a positive integer.')
        except SyntaxError:
            raise commands.BadArgument('Input was not an integer.')

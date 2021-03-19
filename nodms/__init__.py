import json
from pathlib import Path
from redbot.core import commands

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


# Thanks PhenoM4n4n for the before_invoke_hook idea
async def before_invoke_hook(ctx: commands.Context):
    if ctx.channel == ctx.author.dm_channel and ctx.author.id not in ctx.bot.owner_ids:
        raise commands.CheckFailure()


async def setup(bot):
    bot.before_invoke(before_invoke_hook)


def teardown(bot):
    bot.remove_before_invoke_hook(before_invoke_hook)

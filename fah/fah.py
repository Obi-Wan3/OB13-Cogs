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

import aiohttp

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list

FAH = "https://stats.foldingathome.org"


class FaH(commands.Cog):
    """
    Folding@Home Stats

    Various Folding@Home team & donor statistics (https://foldingathome.org/).
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="fah")
    @commands.bot_has_permissions(embed_links=True)
    async def _fah(self, ctx: commands.Context):
        """Folding@Home Team & Donor Statistics"""

    @commands.bot_has_permissions(embed_links=True)
    @_fah.command(name="donor")
    async def _donor(self, ctx: commands.Context, donor_id: int):
        """FaH Donor Statistics"""
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{FAH}/api/donor/{donor_id}") as resp:
                    data = await resp.json()

            if data.get("error"):
                return await ctx.send(f"Error fetching from the Folding@Home API: {data['error']}")

            embed = discord.Embed(
                title=f"{data['name']} ({data['id']})",
                color=await ctx.embed_color(),
                url=f"{FAH}/donor/{donor_id}",
            )
            teams = [f"{t['name']} ({t['team']})" for t in data['teams']]
            embed.add_field(name="Score", value=f"{data['credit']}")
            embed.add_field(name="Rank", value=f"{data['rank']}/{data['total_users']}")
            embed.add_field(name="WUs", value=f"{data['wus']}")
            embed.add_field(name="Team(s)", value=f"""{humanize_list(teams[:min(len(teams), 25)])}""")

            embed.set_author(name="Folding@Home Stats", url="https://stats.foldingathome.org/",
                             icon_url="https://pbs.twimg.com/profile_images/53706032/Fold003_400x400.png")
            embed.set_footer(text="Together we are powerful. | https://foldingathome.org")

        return await ctx.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @_fah.command(name="team")
    async def _team(self, ctx: commands.Context, team_id: int):
        """FaH Team Statistics"""

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{FAH}/api/team/{team_id}") as resp:
                    data = await resp.json()

            if data.get("error"):
                return await ctx.send(f"Error fetching from the Folding@Home API: {data['error']}")

            rank_len = len(data['donors'])
            name_len = len(sorted(data['donors'], key=lambda x: x['name'])[0]['name'])
            score_len = len(str(sorted(data['donors'], key=lambda x: x['credit'])[0]['credit']))
            wus_len = len(str(sorted(data['donors'], key=lambda x: x['wus'])[0]['wus']))

            ldb = f"```{'Rank'.ljust(rank_len+3)}{'Username'.ljust(name_len+3)}{'Score'.ljust(score_len+3)}{'WUs'.ljust(wus_len)}\n"
            ldb += "-"*(len(ldb)-3) + "\n"
            for i in range(min(len(data['donors']), 50)):
                row = data['donors'][i]
                ldb += f"{str(i+1).ljust(rank_len+3)}{str(row['name']).ljust(name_len+3)}{str(row['credit']).ljust(score_len+3)}{str(row['wus']).ljust(wus_len+3)}\n"
            ldb += "```"

            embed = discord.Embed(
                title=f"Team #{data['team']} ({data['name']})",
                color=await ctx.embed_color(),
                url=f"{FAH}/team/{team_id}",
                description=f"**Grand Score:** {data['credit']}\n**Working Units:** {data['wus']}\n**Rank:** {data['rank']}/{data['total_teams']}\n**Homepage:** {data['url']}\n{ldb}"
            )
            embed.set_author(name="Folding@Home Stats", url="https://stats.foldingathome.org/", icon_url="https://pbs.twimg.com/profile_images/53706032/Fold003_400x400.png")
            embed.set_footer(text="Together we are powerful. | https://foldingathome.org")

        return await ctx.send(embed=embed)

    @_fah.command(name="project")
    async def _project(self, ctx: commands.Context, project_id: int):
        """Get a link to an FaH project page."""
        return await ctx.send(f"https://stats.foldingathome.org/project?p={project_id}")

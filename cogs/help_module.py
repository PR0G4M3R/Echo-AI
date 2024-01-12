import discord
from discord.ext import commands
import menus
from typing import Optional
from discord import Embed

def syntax(command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "Optional" in str(value) else f"<{key}>")

    params = " ".join(params)
    return f"```{cmd_and_aliases} {params}```\n{command.brief}"

class HelpMenu(menus.ListPageSource):
    def __init__(self, ctx, categories):
        self.ctx = ctx
        super().__init__(list(categories.keys()), per_page=2)
        self.categories = categories

    async def format_page(self, menu, entries):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.categories)


        embed = Embed(
            title="Help",
            description="What can I help you with?",
            colour=self.ctx.author.colour
        )
        embed.set_thumbnail(url=self.ctx.author.avatar)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} commands.")

        for category in entries:
            cmds_str = "\n\n\u200b".join(self.categories[category])
            embed.add_field(name=f"\u200b{category}\u200b", value=f"\u200b\n{cmds_str}\n\u200b", inline=False)

        return embed

class HelpModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    @commands.command(brief='This command displays this embed.', name="help", extras={"category": "Helpful Commands"})
    async def show_help(self, ctx, cmd: Optional[str]):
        if cmd:
            command = self.bot.get_command(cmd)
            if command:
                await ctx.send(f"{command.name}: {command.brief}")
                return

        # Group commands into categories
        categories = {}
        for command in self.bot.commands:
            category = command.extras.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append(syntax(command))

        # Create a menu and start it
        menu = menus.MenuPages(source=HelpMenu(ctx, categories), clear_reactions_after=True)
        await menu.start(ctx)

def setup(bot):
    bot.add_cog(HelpModule(bot))

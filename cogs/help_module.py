import discord
from discord.ext import commands
from typing import Optional
from discord import Embed
import cogs
from cogs.channel_module import commandInfo
from cogs.member_module import commandInfo
from cogs.moderation_module import commandInfo
from cogs.reminder_module import commandInfo
from cogs.weather_module import commandInfo

class HelpModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    @commands.command(brief='This command displays this embed.', name="help")
    async def show_help(self, ctx, cmd: Optional[str] = None):
        if not cmd:
            # Display the help menu with categories and commands
            await self.display_help_menu(ctx)
        else:
            # Display help for a specific command
            await self.display_command_help(ctx, cmd)

    async def display_help_menu(self, ctx):
        embed = discord.Embed(title="Help Menu", color=discord.Color.green())
        categories = {}
        
        # Collect commands into categories based on catnumber
        for command in self.bot.commands:
            category_number = getattr(command.cog, 'catnumber', None)
            if category_number is not None:
                category_name = command.cog.catname
                if category_number not in categories:
                    categories[category_number] = {'name': category_name, 'commands': []}
                categories[category_number]['commands'].append(command)
        
        # Sort categories by catnumber
        sorted_categories = sorted(categories.values(), key=lambda x: x['name'])
        
        for category in sorted_categories:
            command_list = ""
            for command in category['commands']:
                command_list += f"`{command.name}` - {command.brief}\n"
            embed.add_field(name=category['name'], value=command_list, inline=False)
        
        await ctx.send(embed=embed)

    async def display_command_help(self, ctx, cmd):
        command = self.bot.get_command(cmd)
        if command:
            await ctx.send(f"{command.name}: {command.brief}")
        else:
            await ctx.send("Command not found.")

def setup(bot):
    bot.add_cog(HelpModule(bot))
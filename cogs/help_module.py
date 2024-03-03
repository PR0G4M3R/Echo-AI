import discord
from discord.ext import commands
from typing import Optional
from discord import Embed
from cogs.channel_module import channelCommandInfo
from cogs.member_module import memberCommandInfo
from cogs.moderation_module import moderationCommandInfo
from cogs.reminder_module import reminderCommandInfo
from cogs.weather_module import weatherCommandInfo

class HelpModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    @commands.command(brief='This command displays this embed.', name="help")
    async def show_help(self, ctx, cmd: Optional[str] = None):
        if ctx.invoked_with != "help":  # Check if the command is invoked directly
            return
        
        embed = discord.Embed(title="Help Menu", colour=ctx.author.colour)
        
        # Dictionary to hold commands grouped by categories
        category_commands = {
            "User and Server Info": [],
            "Server Commands": [],
            "Admin Commands": [],
            "Reminders": [],
            "Location Commands": []
        }
        
        # Group commands by category
        for command in self.bot.commands:
            if hasattr(command.cog, 'catname'):
                category_commands[command.cog.catname].append(command)
        
        # Add commands to embed
        for catname, commands_list in category_commands.items():
            command_list = ""
            for command in commands_list:
                command_list += f"`{command.name}` - {command.brief}\n"
            embed.add_field(name=catname, value=command_list, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(HelpModule(bot))

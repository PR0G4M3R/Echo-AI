import discord
from discord.ext import commands
from typing import Optional
from discord import Embed
from cogs.channel_module import channelCommandInfo, CHANNEL_MODULE_COMMANDS
from cogs.member_module import memberCommandInfo, MEMBER_MODULE_COMMANDS
from cogs.moderation_module import moderationCommandInfo, MODERATION_MODULE_COMMANDS
from cogs.reminder_module import reminderCommandInfo, REMINDER_MODULE_COMMANDS
from cogs.weather_module import weatherCommandInfo, WEATHER_MODULE_COMMANDS

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
            "User and Server Info": [CHANNEL_MODULE_COMMANDS],
            "Server Commands": [MEMBER_MODULE_COMMANDS],
            "Admin Commands": [MODERATION_MODULE_COMMANDS],
            "Reminders": [REMINDER_MODULE_COMMANDS],
            "Location Commands": [WEATHER_MODULE_COMMANDS]
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

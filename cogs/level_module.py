from config import levels_module
import discord
from discord.ext import commands

class levelCommandInfo():
    catname = "Leveling"
    catnumber = 6

LEVEL_MODULE_COMMANDS = [
    {"name": "toggle", "brief": "Toggle leveling system on or off."},
    {"name": "view_level", "brief": "View your or another user's level."}
]


import discord
from discord.ext import commands
import os

# Dictionary to store enabled/disabled status for each server
enabled_servers = {}

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_staff_roles(self):
        # Read staff roles from the moderation log file
        staff_roles = []
        with open('logs/moderation_log.txt', 'r') as f:
            for line in f:
                if line.startswith("Assigned roles:"):
                    # Roles are listed after this line
                    for role_line in f:
                        if not role_line.strip():
                            # End of roles section
                            break
                        # Extract role ID from the line and add it to staff_roles
                        role_id = int(role_line.split('(')[-1].split(')')[0])
                        staff_roles.append(role_id)
        return staff_roles

    @commands.command()
    @has_staff_role() 
    async def toggle(self, ctx):
        # Check if the user invoking the command is a staff member
        if not await self.is_staff(ctx):
            return await ctx.send("You do not have permission to use this command.")

        # Toggle leveling system in the current server
        enabled_servers[ctx.guild.id] = not enabled_servers.get(ctx.guild.id, True)
        await ctx.send(f"Leveling system {'enabled' if enabled_servers[ctx.guild.id] else 'disabled'}.")

    @commands.command()
    async def view_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        level = await self.get_level(user.id)
        await ctx.send(f"{user.display_name} is at level {level}.")

def setup(bot):
    bot.add_cog(levelModule(bot))

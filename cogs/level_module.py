from config import levels_module
import discord
from discord.ext import commands
import os
from cogs.moderation_module import has_staff_role

class levelCommandInfo():
    catname = "Leveling"
    catnumber = 6

LEVEL_MODULE_COMMANDS = [
    {"name": "toggle", "brief": "Toggle leveling system on or off."},
    {"name": "view_level", "brief": "View your or another user's level."}
]

# Dictionary to store enabled/disabled status for each server
enabled_servers = {}

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_staff_roles(self, guild_id):
            # Read staff roles from the moderation log file for the given guild_id
            staff_roles = []
            with open(f'logs/moderation_log_{guild_id}.txt', 'r') as f:
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
    async def toggle(self, ctx):
        guild_id = ctx.guild.id
        
        # Check if the user invoking the command has any of the staff roles
        if any(role.id in [r.id for r in ctx.author.roles] for role in staff_roles):
            # User has staff roles
             # Toggle leveling system in the current server
            enabled_servers[ctx.guild.id] = not enabled_servers.get(ctx.guild.id, True)
            await ctx.send(f"Leveling system {'enabled' if enabled_servers[ctx.guild.id] else 'disabled'}.")
            pass
        else:
                await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def view_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        level = await self.get_level(user.id)
        await ctx.send(f"{user.display_name} is at level {level}.")

def setup(bot):
    bot.add_cog(levelModule(bot))

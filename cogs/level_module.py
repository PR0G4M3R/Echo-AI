from config import levels_module
import discord
from discord.ext import commands
import os


class levelCommandInfo():
    catname = "Leveling"
    catnumber = 6

LEVEL_MODULE_COMMANDS = [
    {"name": "toggle", "brief": "Toggle leveling system on or off."},
    {"name": "view_level", "brief": "View your or another user's level."}
]

# Dictionary to store enabled/disabled status for each server
enabled_servers = {}

# Define the increment of XP required for each level
XP_INCREMENT_PER_LEVEL = 5

# Dictionary to store user XP
user_xp = {}

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def update_user_xp(self, user_id, xp):
        # Update user's XP
        if user_id in user_xp:
            user_xp[user_id] += xp
        else:
            user_xp[user_id] = xp

    async def get_level(self, user_id):
        # Calculate user's level based on XP thresholds
        xp = user_xp.get(user_id, 0)
        level = 1
        xp_threshold = XP_INCREMENT_PER_LEVEL
        while xp >= xp_threshold:
            level += 1
            xp_threshold += XP_INCREMENT_PER_LEVEL
        return level

    @commands.Cog.listener()
    async def on_message(self, message):
        # Award 1 XP per message
        await self.update_user_xp(message.author.id, 1)

    def get_staff_roles(self, guild_id):
        # Read staff roles from the moderation log file for the given guild_id
        staff_roles = []
        # Use an absolute path for better reliability
        log_file_path = os.path.join('/app', 'logs', 'moderation_log.txt')
        with open(log_file_path, 'a') as file:
            for line in file:
                if line.startswith("Assigned roles:"):
                    # Roles are listed after this line
                    for role_line in file:
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
        staff_roles = self.get_staff_roles(guild_id)
        
        # Check if the user invoking the command has any of the staff roles
        if any(role in [r.id for r in ctx.author.roles] for role in staff_roles):
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

from config import levels_module
import discord
from discord.ext import commands
import os
import json

class levelCommandInfo():
    catname = "Leveling"
    catnumber = 6

LEVEL_MODULE_COMMANDS = [
    {"name": "toggle", "brief": "Toggle leveling system on or off."},
    {"name": "view_level", "brief": "View your or another user's level."},
    {"name": "set_levelup_channel", "brief":"Set the channel level messages are sent to."}
]

# Dictionary to store enabled/disabled status for each server
enabled_servers = {}

# Define the increment of XP required for each level
XP_INCREMENT_PER_LEVEL = 5

# Dictionary to store user XP
USER_XP_FILE = "user_xp.json"
LEVELUP_CHANNELS_FILE = "levelup_channels.json"

try:
    with open(USER_XP_FILE, "r") as file:
        user_xp = json.load(file)
except FileNotFoundError:
    user_xp = {}

# Load level-up channel data from file
try:
    with open(LEVELUP_CHANNELS_FILE, "r") as file:
        levelup_channels = json.load(file)
except FileNotFoundError:
    levelup_channels = {}

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def update_user_xp(self, user_id, xp):
        # Update user's XP
        if user_id in user_xp:
            user_xp[user_id] += xp
        else:
            user_xp[user_id] = xp

    def save_user_xp(self):
        # Save user XP data to file
        with open(USER_XP_FILE, "w") as file:
            json.dump(user_xp, file)

    async def get_level(self, user_id):
        # Calculate user's level based on XP thresholds
        xp = user_xp.get(user_id, 0)
        level = 1
        xp_threshold = XP_INCREMENT_PER_LEVEL
        while xp >= xp_threshold:
            level += 1
            xp_threshold += XP_INCREMENT_PER_LEVEL
        
        # Check if the user has leveled up compared to their previous level
        prev_level = await self.get_level(user_id) - 1
        if level > prev_level:
            await self.send_level_up_message(user_id, level)
        
        return level

    async def send_level_up_message(self, user_id, level):
        # Send level-up message to the designated channel
        guild = self.bot.get_guild(ctx.guild.id)
        channel_id = levelup_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            user = guild.get_member(user_id)
            if channel and user:
                await channel.send(f"Congratulations to {user.display_name} for reaching level {level}!")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Award 1 XP per message
        await self.update_user_xp(message.author.id, 1)

    def get_staff_roles(self, guild_id):
        # Read staff roles from the moderation log file for the given guild_id
        staff_roles = []
        # Use an absolute path for better reliability
        log_file_path = os.path.join('/app', 'logs', 'moderation_log.txt')
        with open(log_file_path, 'r') as file:
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

    @commands.command()
    async def set_levelup_channel(self, ctx, channel: discord.TextChannel):
        # Set the channel where level-up messages will be sent
        levelup_channels[ctx.guild.id] = channel.id
        await ctx.send(f"Level-up messages will now be sent to {channel.mention}.")

        with open(LEVELUP_CHANNELS_FILE, "w") as file:
                json.dump(levelup_channels, file)

def setup(bot):
    bot.add_cog(levelModule(bot))

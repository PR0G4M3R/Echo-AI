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

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_requirements = [0, 5]  # XP requirements for each level
        self.user_xp = {}  # Dictionary to store user XP across servers

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

    async def track_message(self, user_id, guild_id):
        # Track the user's message and award XP
        xp_gained = 1
        self.user_xp[guild_id][user_id] = self.user_xp[guild_id].get(user_id, 0) + xp_gained
        await self.check_level_up(user_id, guild_id)

    async def check_level_up(self, user_id, guild_id):
        # Check if the user has reached a new level and adjust their level if necessary
        current_xp = self.user_xp[guild_id].get(user_id, 0)
        current_level = self.get_level(current_xp)
        required_xp = self.xp_requirements[current_level + 1]
        if current_xp >= required_xp:
            new_level = self.get_level(current_xp)
            await self.update_level(user_id, guild_id, new_level)

    def get_level(self, xp):
        # Calculate the user's level based on XP
        level = 0
        while xp >= self.xp_requirements[level + 1]:
            level += 1
        return level

    async def update_level(self, user_id, guild_id, new_level):
        # Update the user's level
        self.user_xp[guild_id][user_id] = new_level
        # Optionally, you can send a message or perform other actions when a user levels up

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # Ignore messages from bots
            return
        guild_id = message.guild.id
        user_id = message.author.id
        await self.track_message(user_id, guild_id)

    @commands.command()
    async def view_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        guild_id = ctx.guild.id
        user_xp = self.user_xp.get(guild_id, {}).get(user.id, 0)
        level = self.get_level(user_xp)
        await ctx.send(f"{user.display_name} is at level {level} with {user_xp} XP.")

def setup(bot):
    bot.add_cog(levelModule(bot))

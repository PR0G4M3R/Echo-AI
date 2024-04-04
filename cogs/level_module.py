from config import levels_module
import discord
from discord.ext import commands
import moderation_module
from moderation_module import 


class reminderCommandInfo():
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

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_roles = {}

        # Load staff roles from the file when the bot starts
        self.load_staff_roles()

    def load_staff_roles(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), "..", "logs", "moderation_log.txt")
            with open(file_path, "r") as file:
                for line in file:
                    server_id, role_ids = line.strip().split(":")
                    self.staff_roles[int(server_id)] = [int(role_id) for role_id in role_ids.split(",")]
        except FileNotFoundError:
            print("Staff roles file not found. Skipping loading staff roles.")

    async def is_staff(self, ctx):
        # Check if the user invoking the command has one of the staff roles
        if ctx.guild.id in self.staff_roles:
            member_roles = [role.id for role in ctx.author.roles]
            for role_id in self.staff_roles[ctx.guild.id]:
                if role_id in member_roles:
                    return True
        return False

    @commands.command()
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
    bot.add_cog(Leveling(bot))

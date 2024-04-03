from config import levels_module
import discord
from discord.ext import commands

# Dictionary to store enabled/disabled status for each server
enabled_servers = {}

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user.name}')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if not enabled_servers.get(message.guild.id, True):
            return

        # Your leveling system logic here
        # You can implement leveling system based on message count, etc.
        # For simplicity, let's just acknowledge the message
        print(f"Message received: {message.content}")

def setup(bot):
    bot.add_cog(Leveling(bot))

@commands.command()
async def enable(ctx):
    # Enable leveling system in the current server
    enabled_servers[ctx.guild.id] = True
    await ctx.send("Leveling system enabled.")

@commands.command()
async def disable(ctx):
    # Disable leveling system in the current server
    enabled_servers[ctx.guild.id] = False
    await ctx.send("Leveling system disabled.")

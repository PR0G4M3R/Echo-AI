import discord
from discord.ext import commands, tasks
import os
import random
from itertools import cycle
import asyncio
import cogs
from cogs.message_module import messageModule
from cogs.member_module import memberModule
from cogs.weather_module import weatherModule
from cogs.channel_module import channelModule
from cogs.help_module import HelpModule
from cogs.moderation_module import ModerationModule
from cogs.reminder_module import reminderModule
from cogs.level_module import levelModule

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="Echo_", intents=intents, case_insensitive=True) 
status = variables = [
discord.Game(name='StarMade'),
discord.Activity(type=discord.ActivityType.listening, name='Spotify'),
]


@bot.event
async def on_ready():
    create_database()
    print('Successfully logged in as {0.user}'.format(bot))
    await bot.add_cog(messageModule(bot))
    await bot.add_cog(memberModule(bot))
    await bot.add_cog(weatherModule(bot))
    await bot.add_cog(channelModule(bot))
    await bot.add_cog(HelpModule(bot))
    await bot.add_cog(ModerationModule(bot))
    await bot.add_cog(reminderModule(bot))
    await bot.add_cog(levelModule(bot))
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Starting...'))
    await asyncio.sleep(5)
    status_cycle = cycle(variables)
    while True:
      current_status = next(status_cycle)
      await bot.change_presence(status=discord.Status.online, activity=current_status)
      random_delay = random.uniform(30, 600)  
      await asyncio.sleep(random_delay)
      
bot_token = os.environ.get('TOKEN')
bot.run(bot_token)
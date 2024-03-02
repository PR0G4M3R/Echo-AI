import discord
from discord.ext import commands, tasks
import os
import random
from itertools import cycle
import asyncio
import cogs
from cogs.message_module import messageModule
from cogs.member_module import memberModule, create_database
from cogs.weather_module import weatherModule
from cogs.channel_module import channelModule
from cogs.help_module import HelpModule
from cogs.moderation_module import ModerationModule
from cogs.chatbot_module import chatbotModule
from cogs.reminder_module import reminderModule
from cogs.active import activeModule

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="Echo_", intents=intents, case_insensitive=True) 
status = variables = [
discord.Game(name='Minecraft'),
discord.Activity(type=discord.ActivityType.listening, name='Spotify'),
discord.Game(name='Crossout'),
]


@bot.event
async def on_ready():
    create_database()
    print('Successfully logged in as {0.user}'.format(bot))
    bot.add_cog(messageModule(bot))
    bot.add_cog(memberModule(bot))
    bot.add_cog(weatherModule(bot))
    bot.add_cog(channelModule(bot))
    bot.add_cog(HelpModule(bot))
    bot.add_cog(ModerationModule(bot))
    bot.add_cog(chatbotModule(bot))
    bot.add_cog(reminderModule(bot))
    bot.add_cog(activeModule(bot))
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Starting...'))
    await asyncio.sleep(5)
    status_cycle = cycle(variables)
    while True:
      current_status = next(status_cycle)
      await bot.change_presence(status=discord.Status.online, activity=current_status)
      random_delay = random.uniform(15, 600)  
      await asyncio.sleep(random_delay)
      
bot_token = os.environ.get('TOKEN')
bot.run(bot_token)
import os
import discord
from discord.ext import commands

class messageModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
          await self.filter_message(message)

    async def filter_message(self, message):
        filter_words = ("HCDV887", "nigger" , "nigga" , "nig" , "nigg" , "nigg3r" , "nigg4" , "nigg" , "pervert" , "perv" , "perv3r" , "perv4r" , "perv5" , "perv6" , "perv7")  
        if any(word in message.content for word in filter_words):
            await message.delete()
           
async def setup(bot):
    await bot.add_cog(messageModule(bot))
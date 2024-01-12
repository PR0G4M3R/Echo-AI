import discord
from discord.ext import commands
import random


class chatbotModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        else:
            prompts = ('Hey', 'Hi', 'Hello', 'Yo', 'Sup')
            for prompt in prompts:
                if message.content.startswith(f"Echo {prompt}"):
                    await message.channel.send(f"{random.choice(prompts)} {message.author.mention}")
                    break

def setup(bot):
    bot.add_cog(chatbotModule(bot))

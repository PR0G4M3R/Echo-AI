from discord.ext import commands, tasks
import asyncio

class activeModule(commands.Cog):
  def __init__(self, bot):
      self.bot = bot
      self.update_status.start()

  @tasks.loop(minutes=7)
  async def update_status(self):
      channel = self.bot.get_channel(1194884556059312189)
      if channel:
          await channel.send("Running...")

def setup(bot):
  bot.add_cog(activeModule(bot))
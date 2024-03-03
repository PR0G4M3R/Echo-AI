from datetime import datetime
from typing import Optional
import os
from discord import Embed, Member
from discord.ext import commands

class commandInfo():
    catname = "User and Server Info"
    catnumber = 1
class channelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(brief='This command gets the user info of yourself or another user.', name="userinfo", aliases=["memberinfo", "ui", "mi"])
    async def user_info(self, ctx, target: Optional[Member] = None):
        target = target or ctx.author
        embed = Embed(
            title="User Information",
            colour=target.colour,
            timestamp=datetime.utcnow())     

        fields = [("Name", str(target), True),
                  ("ID", target.id, True),
                  ("Bot", target.bot, True),
                  ("Top role", target.top_role.mention, True),
                  ("Status", str(target.status).title(), True),
                  ("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
                  ("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("Boosted", bool(target.premium_since), True)]  
        for name, value, inline in fields:
          embed.add_field(name=name, value=value, inline=inline)
        await ctx.send(embed=embed)
                  
  
    @commands.command(brief='This command gets the info of the server it is used in.', name="serverinfo", aliases=["guildinfo", "si", "gi"])
    async def server_info(self, ctx):
        banned_users = await ctx.guild.bans()
        banned_users_string = ""
        count = 0
        for entry in banned_users:
            banned_users_string += f"{entry.user.name}#{entry.user.discriminator}\n"
            count += 1
            if count >= 10:
                break
            
        embed = Embed(
            title="Server Information",
            colour=ctx.guild.owner.colour,
            timestamp=datetime.utcnow())  
        statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]
        invites_length = len(await ctx.guild.invites())
        invites_value = str(invites_length)[:1021] + "..." if invites_length > 1021 else str(invites_length)
        
        fields = [("ID", ctx.guild.id, True),
                ("Owner", ctx.guild.owner, True),
                ("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                ("Members", len(ctx.guild.members), True),
                ("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
                ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
                ("Banned members", banned_users_string, True),
                ("Statuses", f"● {statuses[0]} ● {statuses[1]} ● {statuses[2]} ○ {statuses[3]}", True),
                ("Text channels", len(ctx.guild.text_channels), True),
                ("Voice channels", len(ctx.guild.voice_channels), True),
                ("Categories", len(ctx.guild.categories), True),
                ("Roles", len(ctx.guild.roles), True),
                ("Invites", invites_value, True),
                ("\u200b", "\u200b", True)]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
          self.bot.cogs_ready.ready_up("info")

def setup(bot):
    bot.add_cog(channelModule(bot))

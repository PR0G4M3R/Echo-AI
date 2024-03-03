from datetime import datetime, timedelta
import discord
from discord import Embed, DMChannel
from discord.ext import commands
import asyncio
import re
import datetime
import pytz
from config import modmail_module

date_today_PST = datetime.datetime.now(pytz.timezone('UTC'))
date_str = date_today_PST.strftime("%m/%d/%Y")
time_str = date_today_PST.strftime("%H:%M:%S")

def is_guild_owner():
    async def predicate(ctx):
        return ctx.author == ctx.guild.owner
    return commands.check(predicate)

class moderationCommandInfo():
    catname = "Admin Commands"
    catnumber = 3

MODERATION_MODULE_COMMANDS = [
    {"name": "setup_roles", "brief": "Set the staff roles for the moderator commands."},
    {"name": "modmail", "brief": "Send a message to mods"},
    {"name": "mute", "brief": "Mute members"},
    {"name": "unmute", "brief": "Unmute members"},
    {"name": "kick", "brief": "This kicks a user."},
    {"name": "ban", "brief": "This bans a user."},
    {"name": "unban", "brief": "This unbans a user."}
]    
class ModerationModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 1113493098090209392  # Replace this with the actual channel ID
        self.top_3_role_ids = {}  # Dictionary to store top 3 role IDs for each server

    @commands.command(brief="Set the staff roles for the moderator commands.", name="setup_roles")
    @is_guild_owner()
    async def setup_roles(self, ctx, role1: discord.Role, role2: discord.Role, role3: discord.Role):
        # Store the role IDs in the dictionary for the current server
        self.top_3_role_ids[ctx.guild.id] = [role1.id, role2.id, role3.id]

        await ctx.send(f"Staff roles for the moderator commands have been set.\n"
                       f"Role 1: {role1.mention}\n"
                       f"Role 2: {role2.mention}\n"
                       f"Role 3: {role3.mention}")
        file = open('logs/moderation_log.txt', 'a')
        file.write(f'{date_str}, {time_str}\n')
        file.write(f'Staff roles for the moderator commands have been set in {ctx.guild}')
        file.close()

    @commands.command(brief='Send a message to mods', name="modmail")
    @commands.cooldown(1, 900, commands.BucketType.user)  # 1 use every 900 seconds (15 minutes) per user
    async def getmail(self, ctx, *, content: str):  # Use * to collect entire message as one string
      if modmail_module:
        try:
            if len(content) < 30:
                await ctx.send("Your message should be at least 30 characters in length.")
            else:
                embed = Embed(title="Modmail",
                              colour=ctx.author.colour,
                              timestamp=datetime.utcnow())

                embed.set_thumbnail(url=ctx.author.avatar.url)

                fields = [("Member", ctx.author.display_name, False),
                          ("Message", content, False)]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                if self.log_channel:
                    channel = self.bot.get_channel(self.log_channel)
                    if channel:
                        await channel.send(embed=embed)
                        await ctx.send("Message sent to moderators on your behalf.")
                    else:
                        await ctx.send("Oops! The log channel was not found.")
                else:
                    await ctx.send("Oops! An error occurred while sending the message to moderators. Log channel ID is missing.")
        except commands.CommandOnCooldown as e:
            await ctx.message.delete()
            await ctx.send(f"Sorry, you are on cooldown. Please wait {e.retry_after:.0f} seconds before using the command again.", delete_after=5)

    @getmail.error
    async def getmail_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.delete()
            await ctx.send(f"Sorry, you are on cooldown. Please wait {error.retry_after:.0f} seconds before using the command again.", delete_after=5)

    @commands.command(brief="Mute members", name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, duration: str = None, *, reason: str = "No reason provided."):
        if member is None:
            await ctx.send("Please mention a member to mute.")
            return

        if not member.bot:  # Make sure to exclude bots from being muted
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not muted_role:
                await ctx.send("The 'Muted' role is not found. Make sure you have created the 'Muted' role.")
                return

            member_roles = member.roles[1:]  # Exclude the @everyone role

            await member.edit(roles=[muted_role])

            await ctx.send(f"{member.mention} has been muted.")
            file = open('logs/moderation_log.txt', 'a')
            file.write(f'{date_str}, {time_str}\n')
            file.write(f'Member {member.user} has been muted in {ctx.guild}')
            file.close()

            if duration:
                # Parse the duration using the "parse_duration" function
                seconds = self.parse_duration(duration)
                if seconds is None:
                    await ctx.send("Invalid duration format. Please use a valid duration format (e.g., '10s', '1h', '30m').")
                    return

                await asyncio.sleep(seconds)
                # Restore the roles to the member after the mute duration
                await member.edit(roles=member_roles)
                await ctx.send(f"{member.mention} has been unmuted after {duration}.")
                file = open('logs/moderation_log.txt', 'a')
                file.write(f'{date_str}, {time_str}\n')
                file.write(f'Member {member.user} has been unmuted in {ctx.guild}')
                file.close()

    @commands.command(brief="Unmute members", name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None):
        if member is None:
            await ctx.send("Please mention a member to unmute.")
            return

        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await ctx.send("The 'Muted' role is not found. Make sure you have created the 'Muted' role.")
            return

        if muted_role not in member.roles:
            await ctx.send(f"{member.mention} is not muted.")
            return

        # Get the stored roles of the member
        stored_roles = self.get_stored_roles(member)

        await member.edit(roles=stored_roles)
        await ctx.send(f"{member.mention} has been unmuted.")
        file = open('logs/moderation_log.txt', 'a')
        file.write(f'{date_str}, {time_str}\n')
        file.write(f'Member {member.user} has been unmuted in {ctx.guild}')
        file.close()

    def get_stored_roles(self, member):
        # Get the stored roles of the member from the top_3_role_ids dictionary
        guild_id = member.guild.id
        top_3_role_ids = self.top_3_role_ids.get(guild_id)

        if top_3_role_ids:
            stored_roles = [role for role in member.roles if role.id in top_3_role_ids]
        else:
            stored_roles = []

        return stored_roles

    def parse_duration(self, duration):
        # Regular expression to match the duration format (e.g., '10s', '1h', '30m')
        duration_pattern = re.compile(r"^(\d+)([smh])$")
        match = duration_pattern.match(duration)

        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            if unit == "s":
                return amount
            elif unit == "m":
                return amount * 60
            elif unit == "h":
                return amount * 3600

        return None

#KICKING &/OR BANNING MEMBERS
    @commands.command(brief='This kicks a user.', name="kick")
    @commands.has_permissions(kick_members=True)
    @is_guild_owner()
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked for: {reason}.")
            file = open('logs/moderation_log.txt', 'a')
            file.write(f'{date_str}, {time_str}\n')
            file.write(f'Member {member.user} has been kicked from {ctx.guild} for: {reason}')
            file.close()
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to kick members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to kick the member.")

    @commands.command(brief='This bans a user.', name="ban")
    @commands.has_permissions(ban_members=True)
    @is_guild_owner()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned for: {reason}.")
            file = open('logs/moderation_log.txt', 'a')
            file.write(f'{date_str}, {time_str}\n')
            file.write(f'Member {member.user} has been banned from {ctx.guild} for: {reason}')
            file.close()
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to ban members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to ban the member.")

    @commands.command(brief='This unbans a user.', name="unban")
    @commands.has_permissions(ban_members=True)
    @is_guild_owner()
    async def unban(self, ctx, *, member_id: int):
        try:
            banned_users = await ctx.guild.bans()
            for ban_entry in banned_users:
                if ban_entry.user.id == member_id:
                    await ctx.guild.unban(ban_entry.user)
                    await ctx.send(f"{ban_entry.user.mention} has been unbanned.")
                    file = open('logs/moderation_log.txt', 'a')
                    file.write(f'{date_str}, {time_str}\n')
                    file.write(f'Member {ban_entry.user} has been unbanned in {ctx.guild}')
                    file.close()
                    return

            await ctx.send("User not found in the ban list.")
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to unban members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to unban the member.")





def setup(bot):
    bot.add_cog(ModerationModule(bot))

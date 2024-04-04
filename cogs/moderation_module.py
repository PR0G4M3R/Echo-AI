from datetime import datetime, timedelta
import discord
from discord import Embed, DMChannel
from discord.ext import commands
import asyncio
import re
import sqlite3
import datetime
import pytz
import os
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
        self.connection = sqlite3.connect('moderation.db')
        self.cursor = self.connection.cursor()

        # Call create_tables method with await
        asyncio.create_task(self.create_tables())

    async def create_tables(self):
        # Check if the moderation_log table exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moderation_log'")
        table_exists = self.cursor.fetchone() is not None
        if not table_exists:
            # Table doesn't exist, create it
            self.cursor.execute('''CREATE TABLE moderation_log (
                                    id INTEGER PRIMARY KEY,
                                    guild_id INTEGER,
                                    mod_id INTEGER,
                                    target_id INTEGER,
                                    action TEXT,
                                    reason TEXT
                                  )''')
            # Commit the transaction to save the changes
            self.connection.commit()

    # Function to execute SQL queries
    def execute_query(self, query, values=None):
        if values:
            c.execute(query, values)
        else:
            c.execute(query)
        conn.commit()

    @commands.command(brief="Set the staff roles for the moderator commands.", name="setup_roles")
    @is_guild_owner()
    async def setup_roles(self, ctx, *roles: discord.Role):
        if len(roles) < 1:
            return await ctx.send("Please provide at least one role.")

        role_ids = [role.id for role in roles[:3]]  # Limit to top 3 roles if more than 3 are provided
        self.top_3_role_ids[ctx.guild.id] = role_ids

        roles_mentions = "\n".join([f"Role {i+1}: {role.mention}" for i, role in enumerate(roles)])
        await ctx.send(f"Staff roles for the moderator commands have been set:\n{roles_mentions}")
        
        # Log the moderation action
        await self.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "Setup Roles", "Roles were setup")
        
        # Save top 3 role IDs to the SQLite database
        self.save_top_roles(ctx.guild.id, role_ids)

    async def save_top_roles(self, guild_id, role_ids):
        # Save top 3 role IDs to SQLite database
        query = '''INSERT INTO top_roles (guild_id, role_1, role_2, role_3) VALUES (?, ?, ?, ?)'''
        values = (guild_id, *role_ids, *[None] * (3 - len(role_ids)))  # Fill with None if less than 3 roles provided
        self.execute_query(query, values)

    def save_moderation_log(self):
        # Save moderation log to SQLite database
        timestamp = str(datetime.datetime.now(pytz.timezone('UTC')))
        query = '''INSERT INTO moderation_log (timestamp, action, roles) VALUES (?, ?, ?)'''
        values = (timestamp, log_entry["action"], ", ".join(log_entry["roles"]))
        self.execute_query(query, values)

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

    # Mute command
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
            await self.log_action(ctx.guild.id, "Mute", member.id, reason)

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
                await self.log_action(ctx.guild.id, "Unmute", member.id, reason="Mute expired")

    # Unmute command
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
        await self.log_action(ctx.guild.id, "Unmute", member.id, reason="Manual unmute")

    @commands.command(brief="Kick members", name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided."):
        if member is None:
            await ctx.send("Please mention a member to kick.")
            return

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked.")
            await self.log_action(ctx.guild.id, "Kick", member.id, reason)
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick members.")
        except discord.HTTPException:
            await ctx.send("Failed to kick the member. Please try again later.")

    def get_stored_roles(self, member):
        # Get the stored roles of the member from the top_3_role_ids dictionary
        guild_id = member.guild.id

    async def log_action(self, guild_id, action, member_id, reason=None):
        timestamp = str(datetime.datetime.now(pytz.timezone('UTC')))
        log_entry = {"timestamp": timestamp, "action": action, "member_id": member_id, "reason": reason}
        self.save_log(guild_id, log_entry)

    def save_log(self, guild_id, log_entry):
        conn = sqlite3.connect('moderation_logs.db')
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
                            guild_id INTEGER,
                            timestamp TEXT,
                            action TEXT,
                            member_id INTEGER,
                            reason TEXT
                          )''')

        cursor.execute('''INSERT INTO moderation_logs (guild_id, timestamp, action, member_id, reason)
                          VALUES (?, ?, ?, ?, ?)''', (guild_id, log_entry['timestamp'], log_entry['action'], log_entry['member_id'], log_entry.get('reason', None)))

        conn.commit()
        conn.close()

    # Ban command
    @commands.command(brief='This bans a user.', name="ban")
    @commands.has_permissions(ban_members=True)
    @is_guild_owner()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned for: {reason}.")
            await self.log_action(ctx.guild.id, "Ban", member.id, reason)
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to ban members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to ban the member.")

    # Unban command
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
                    await self.log_action(ctx.guild.id, "Unban", member.id, reason)
                    return

            await ctx.send("User not found in the ban list.")
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to unban members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to unban the member.")

def setup(bot):
    bot.add_cog(ModerationModule(bot))
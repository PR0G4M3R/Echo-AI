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
import psycopg2
from config import modmail_module

# Get the DATABASE_URL environment variable from Railway
MDB_URL = os.getenv('MDB_URL')
LDB_URL = os.getenv('LDB_URL')
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
    {"name": "setlc", "brief": "Set the log channel for the server."},
    {"name": "modmail", "brief": "Send a message to mods."},
    {"name": "mute", "brief": "Mute members."},
    {"name": "unmute", "brief": "Unmute members."},
    {"name": "kick", "brief": "This kicks a user."},
    {"name": "ban", "brief": "This bans a user."},
    {"name": "unban", "brief": "This unbans a user."}
]

class ModerationModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 1113493098090209392  # Replace this with the actual channel ID
        self.top_3_role_ids = {}  # Dictionary to store top 3 role IDs for each server
        # Connect to the moderation database using the MDB_URL environment variable
        self.connection = psycopg2.connect(os.getenv('MDB_URL'))
        self.cursor = self.connection.cursor()

        # Call create_tables method with await
        asyncio.create_task(self.create_tables())

    async def create_tables(self):
    # Create tables if they don't exist in the moderation database
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation_log (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                mod_id BIGINT,
                target_id BIGINT,
                action TEXT,
                reason TEXT
            );

            CREATE TABLE IF NOT EXISTS member_roles (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                member_id BIGINT,
                role_ids BIGINT[]  # Array of role IDs
            );
        ''')
        self.connection.commit()

    async def get_stored_roles(self, member):
    # Connect to your database
        self.cursor.execute("SELECT role_ids FROM member_roles WHERE member_id = %s AND guild_id = %s", (member.id, member.guild.id))
        role_ids_record = self.cursor.fetchone()

        if role_ids_record:
            # Convert the role IDs stored in the database to discord.Role objects
            role_ids = role_ids_record[0]  # Assuming 'role_ids' is stored as an array
            roles = [member.guild.get_role(role_id) for role_id in role_ids if member.guild.get_role(role_id)]
            return roles
        else:
            # Return an empty list if no roles are found
            return []


        # Function to execute SQL queries
        def execute_query(self, query, values=None):
            if values:
                self.cursor.execute(query, values)
            else:
                self.cursor.execute(query)
            self.connection.commit()

    @commands.command(brief="Set the staff roles for the moderator commands.", name="setup_roles")
    @commands.is_owner()
    async def setup_roles(self, ctx, *roles: discord.Role):
        if len(roles) < 1:
            return await ctx.send("Please provide at least one role.")

        role_ids = [role.id for role in roles[:3]]  # Limit to top 3 roles if more than 3 are provided
        # Save top 3 role IDs to the PostgreSQL database
        self.save_top_roles(ctx.guild.id, role_ids)

        roles_mentions = "\n".join([f"Role {i+1}: {role.mention}" for i, role in enumerate(roles)])
        await ctx.send(f"Staff roles for the moderator commands have been set:\n{roles_mentions}")
        
        # Log the moderation action
        await self.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "Setup Roles", "Roles were setup")

    async def save_top_roles(self, guild_id, role_ids):
        # Save top 3 role IDs to PostgreSQL database
        query = '''
            INSERT INTO top_roles (guild_id, role_1, role_2, role_3)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (guild_id)
            DO UPDATE SET role_1 = EXCLUDED.role_1, role_2 = EXCLUDED.role_2, role_3 = EXCLUDED.role_3
        '''
        values = (guild_id, *role_ids, *[None] * (3 - len(role_ids)))  # Fill with None if less than 3 roles provided
        self.cursor.execute(query, values)
        self.connection.commit()

    async def log_moderation_action(self, guild_id, mod_id, target_id, action, reason):
        # Log moderation action to PostgreSQL database
        timestamp = datetime.datetime.now(pytz.timezone('UTC')).strftime("%Y-%m-%d %H:%M:%S")
        query = '''
            INSERT INTO moderation_log (guild_id, mod_id, target_id, action, reason, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        '''
        values = (guild_id, mod_id, target_id, action, reason, timestamp)
        self.cursor.execute(query, values)
        self.connection.commit()

    @commands.command(brief='Send a message to mods', name="modmail")
    @commands.cooldown(1, 900, commands.BucketType.user)  # 1 use every 900 seconds (15 minutes) per user
    async def getmail(self, ctx, *, content: str):  # Use * to collect entire message as one string
        if len(content) < 30:
            await ctx.send("Your message should be at least 30 characters in length.")
            return

        # Fetch the log channel ID from the database
        log_channel_id = await self.fetch_log_channel(ctx.guild.id)
        if log_channel_id is None:
            await ctx.send("Oops! An error occurred while sending the message to moderators. Log channel ID is missing.")
            return

        embed = Embed(title="Modmail",
                      colour=ctx.author.colour,
                      timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=ctx.author.avatar.url)
        fields = [("Member", ctx.author.display_name, False),
                  ("Message", content, False)]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        channel = self.bot.get_channel(log_channel_id)
        if channel:
            await channel.send(embed=embed)
            await ctx.send("Message sent to moderators on your behalf.")
        else:
            await ctx.send("Oops! The log channel was not found.")

    async def fetch_log_channel(self, guild_id):
        # Fetch the log channel ID from the moderation database
        self.cursor.execute('SELECT channel_id FROM log_channels WHERE guild_id = %s', (guild_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    @getmail.error
    async def getmail_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.delete()
            await ctx.send(f"Sorry, you are on cooldown. Please wait {error.retry_after:.0f} seconds before using the command again.", delete_after=error.retry_after)
        else:
            await ctx.send("An unexpected error occurred. Please try again later.")
    
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
            await self.log_moderation_action(ctx.guild.id, "Mute", member.id, reason)

            if duration:
                seconds = self.parse_duration(duration)
                if seconds is None:
                    await ctx.send("Invalid duration format. Please use a valid duration format (e.g., '10s', '1h', '30m').")
                    return

                await asyncio.sleep(seconds)
                await member.edit(roles=member_roles)
                await ctx.send(f"{member.mention} has been unmuted after {duration}.")
                await self.log_moderation_action(ctx.guild.id, "Unmute", member.id, reason="Mute expired")
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
        await self.log_moderation_action(ctx.guild.id, "Unmute", member.id, reason="Manual unmute")

    @commands.command(brief="Kick members", name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided."):
        if member is None:
            await ctx.send("Please mention a member to kick.")
            return

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked.")
            await self.log_moderation_action(ctx.guild.id, "Kick", member.id, reason)
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick members.")
        except discord.HTTPException:
            await ctx.send("Failed to kick the member. Please try again later.")
    
    # Ban command
    @commands.command(brief='This bans a user.', name="ban")
    @commands.has_permissions(ban_members=True)
    @is_guild_owner()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned for: {reason}.")
            await self.log_moderation_action(ctx.guild.id, "Ban", member.id, reason)
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
                    await self.log_moderation_action(ctx.guild.id, "Unban", ban_entry.user.id, "Manual unban")
                    return

            await ctx.send("User not found in the ban list.")
        except discord.Forbidden:
            await ctx.send("I do not have the required permissions to unban members.")
        except discord.HTTPException:
            await ctx.send("An error occurred while trying to unban the member.")

    @commands.command(name='setlogchannel')
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        # Check if the user is the guild owner
        if ctx.author == ctx.guild.owner:
            # Store the log channel in the moderation database
            self.cursor.execute('''
                INSERT INTO log_channels (guild_id, channel_id)
                VALUES (%s, %s)
                ON CONFLICT (guild_id)
                DO UPDATE SET channel_id = EXCLUDED.channel_id
            ''', (ctx.guild.id, channel.id))
            self.connection.commit()
            await ctx.send(f"Log channel set to {channel.mention}.")
        else:
            await ctx.send("You do not have permission to set the log channel.")

def setup(bot):
    bot.add_cog(ModerationModule(bot))
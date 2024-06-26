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



def is_staff():
    async def predicate(ctx):
        # Retrieve the database URL for the staff roles from the environment variable
        # Establish a connection to the MDB database
        conn = psycopg2.connect(MDB_URL)
        cursor = conn.cursor()

        # Fetch the staff role IDs from the MDB database
        cursor.execute("SELECT role_1, role_2, role_3, role_4, role_5 FROM top_roles WHERE guild_id = %s", (ctx.guild.id,))
        row = cursor.fetchone()
        conn.close()

        # Check if the member has one of the staff roles
        if row:
            staff_role_ids = [role_id for role_id in row if role_id]
            return any(role.id in staff_role_ids for role in ctx.author.roles)
        return False
    return commands.check(predicate)

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
        try:
            # Create tables if they don't exist in the moderation database
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_log (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    mod_id BIGINT,
                    target_id BIGINT,
                    action TEXT,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS member_roles (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    member_id BIGINT,
                    role_ids BIGINT[]  -- Array of role IDs
                );
                CREATE TABLE IF NOT EXISTS top_roles (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    role_1 BIGINT,
                    role_2 BIGINT,
                    role_3 BIGINT,
                    role_4 BIGINT,
                    role_5 BIGINT
                );
            ''')
            self.connection.commit()
        except psycopg2.Error as e:
            print("Error creating tables:", e)
            self.connection.rollback()  # Rollback transaction in case of error

    async def log_moderation_action(self, guild_id, mod_id, target_id, action, reason):
        try:
            # Open cursor
            cursor = self.connection.cursor()

            # Execute INSERT statement to log the moderation action
            cursor.execute("""
                INSERT INTO moderation_log (guild_id, mod_id, target_id, action, reason)
                VALUES (%s, %s, %s, %s, %s)
            """, (guild_id, mod_id, target_id, action, reason))

            # Commit changes
            self.connection.commit()
        except psycopg2.Error as e:
            print("Error logging moderation action:", e)
            self.connection.rollback()  # Rollback transaction in case of error


    @commands.command(brief="Set the staff roles for the moderator commands.", name="setup_roles")
    @is_guild_owner()
    async def setup_roles(self, ctx, *roles: discord.Role):
        if len(roles) < 1:
            return await ctx.send("Please provide at least one role.")

        role_ids = [role.id for role in roles[:3]]  # Limit to top 3 roles if more than 3 are provided
        # Save top 3 role IDs to the PostgreSQL database
        await self.save_top_roles(ctx.guild.id, role_ids)

        roles_mentions = "\n".join([f"Role {i+1}: {role.mention}" for i, role in enumerate(roles)])
        await ctx.send(f"Staff roles for the moderator commands have been set:\n{roles_mentions}")
        
        # Log the moderation action
        await self.log_moderation_action(ctx.guild.id, ctx.author.id, ctx.author.id, "Setup Roles", "Roles were setup")

    async def save_top_roles(self, guild_id, role_ids):
        try:
            # Open cursor
            cursor = self.connection.cursor()

            # Build the SQL query dynamically based on the number of roles
            placeholders = ','.join(['%s'] * len(role_ids))
            columns = ','.join([f'role_{i}' for i in range(1, len(role_ids) + 1)])
            query = f"INSERT INTO top_roles (guild_id, {columns}) VALUES (%s, {placeholders})"

            # Execute the SQL query
            cursor.execute(query, (guild_id, *role_ids))

            # Commit changes
            self.connection.commit()
        except psycopg2.Error as e:
            print("Error saving top roles:", e)
            self.connection.rollback()  # Rollback transaction in case of error

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
    
    #Mute
    @commands.command(brief="Mute members", name="mute")
    @is_staff()
    async def mute(self, ctx, member: discord.Member = None, duration: str = None, *, reason: str = "No reason provided."):
        if member is None:
            await ctx.send("Please mention a member to mute.")
            return

        if not member.bot:  # Make sure to exclude bots from being muted
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not muted_role:
                await ctx.send("The 'Muted' role is not found. Make sure you have created the 'Muted' role.")
                return

            member_roles = [role.id for role in member.roles if role != muted_role]  # Exclude the 'Muted' role

            # Store the member's roles before muting
            await self.store_member_roles(ctx.guild.id, member.id, member_roles)

            await member.edit(roles=[muted_role])

            await ctx.send(f"{member.mention} has been muted.")
            await self.log_moderation_action(ctx.guild.id, ctx.author.id, member.id, "Mute", reason)  # Pass reason to log_moderation_action

            if duration:
                seconds = self.parse_duration(duration)
                if seconds is None:
                    await ctx.send("Invalid duration format. Please use a valid duration format (e.g., '10s', '1h', '30m').")
                    return

                await asyncio.sleep(seconds)
                # Retrieve member's roles from database
                stored_roles = await self.get_stored_roles(ctx.guild.id, member.id)
                if stored_roles:
                    await member.edit(roles=stored_roles)
                    await ctx.send(f"{member.mention} has been unmuted after {duration}.")
                    await self.log_moderation_action(ctx.guild.id, "Unmute", member.id, reason="Mute expired")
                else:
                    await ctx.send("Error: Could not retrieve stored roles for the member.")


    #Unmute
    @commands.command(brief="Unmute members", name="unmute")
    @is_staff()
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

        # Restore the member's roles
        stored_roles = await self.get_stored_roles(ctx.guild.id, member.id)
        if stored_roles:
            await member.edit(roles=stored_roles)
            await ctx.send(f"{member.mention} has been unmuted.")
            await self.log_moderation_action(ctx.guild.id, ctx.author.id, member.id, "Unmute", reason="Manual unmute")
        else:
            await ctx.send("Error: Could not retrieve stored roles for the member.")

    async def store_member_roles(self, guild_id, member_id, roles):
        try:
            self.cursor.execute('''
                INSERT INTO member_roles (guild_id, member_id, role_ids)
                VALUES (%s, %s, %s)
                ON CONFLICT (guild_id, member_id) DO UPDATE
                SET role_ids = EXCLUDED.role_ids;
            ''', (guild_id, member_id, roles))
            self.connection.commit()
        except psycopg2.Error as e:
            print("Error storing member roles:", e)
            self.connection.rollback()

    async def get_stored_roles(self, guild_id, member_id):
        try:
            self.cursor.execute('''
                SELECT role_ids
                FROM member_roles
                WHERE guild_id = %s AND member_id = %s;
            ''', (guild_id, member_id))
            result = self.cursor.fetchone()
            if result:
                role_ids = result[0]
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                roles = [discord.utils.get(guild.roles, id=role_id) for role_id in role_ids]
                return roles
            else:
                return None
        except psycopg2.Error as e:
            print("Error retrieving stored roles:", e)
            return None



    @commands.command(brief="Kick members", name="kick")
    @is_staff()
    async def kick(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided."):
        if member is None:
            await ctx.send("Please mention a member to kick.")
            return

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked.")
            await self.log_moderation_action(ctx.guild.id, ctx.author.id, member.id, "Kick", reason)

        except discord.Forbidden:
            await ctx.send("I don't have permission to kick members.")
        except discord.HTTPException:
            await ctx.send("Failed to kick the member. Please try again later.")
    
    # Ban command
    @commands.command(brief='This bans a user.', name="ban")
    @is_staff()
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
    @is_staff()
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
    @is_staff()
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

async def setup(bot):
    await bot.add_cog(ModerationModule(bot))
    
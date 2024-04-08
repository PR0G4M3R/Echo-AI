import discord
from discord.ext import commands
import sqlite3
import os
import asyncio
import os
import psycopg2

MDB_URL = os.getenv('MDB_URL')
LDB_URL = os.getenv('LDB_URL')

def is_staff():
    async def predicate(ctx):
        try:
            # Establish a connection to the MDB database
            conn = psycopg2.connect(MDB_URL)
            cursor = conn.cursor()

            # Fetch non-null staff role IDs from the MDB database
            cursor.execute("""
                SELECT role_1, role_2, role_3, role_4, role_5 
                FROM top_roles 
                WHERE guild_id = %s
            """, (ctx.guild.id,))
            row = cursor.fetchone()
            
            # Close the database connection
            conn.close()

            # Check if the member has one of the staff roles
            if row:
                staff_role_ids = [role_id for role_id in row if role_id]
                return any(role.id in staff_role_ids for role in ctx.author.roles)
            return False
        except Exception as e:
            print("Error in is_staff predicate:", e)
            return False

    return commands.check(predicate)



class levelCommandInfo():
    catname = "Leveling"
    catnumber = 6

LEVEL_MODULE_COMMANDS = [
    {"name": "toggle", "brief": "Toggle leveling system on or off."},
    {"name": "view_level", "brief": "View your or another user's level."},
    {"name": "set_levelup_channel", "brief":"Set the channel level messages are sent to."}
]

# Define the increment of XP required for each level
XP_INCREMENT_PER_LEVEL = 5

class levelModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to the leveling database using the ldb_url environment variable
        self.ldb_connection = psycopg2.connect(os.getenv('LDB_URL'))
        self.ldb_cursor = self.ldb_connection.cursor()
        # Connect to the moderation database using the mdb_url environment variable
        self.mdb_connection = psycopg2.connect(os.getenv('MDB_URL'))
        self.mdb_cursor = self.mdb_connection.cursor()
        asyncio.create_task(self.create_tables())

    async def get_top_roles(self, guild_id):
        # Retrieve staff roles from the moderation database
        top_roles = []
        self.mdb_cursor.execute('SELECT role_1, role_2, role_3, role_4, role_5 FROM top_roles WHERE guild_id = %s', (guild_id,))
        rows = self.mdb_cursor.fetchall()
        for row in rows:
            top_roles.append(row[0])
        return top_roles

    async def create_tables(self):
    # Create tables if they don't exist in the leveling database
        self.ldb_cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_xp (
                user_id BIGINT PRIMARY KEY,
                xp BIGINT
            )
        ''')
        self.ldb_cursor.execute('''
            CREATE TABLE IF NOT EXISTS levelup_channels (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT
            )
        ''')
        self.ldb_cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_levels (
                user_id BIGINT PRIMARY KEY,
                level INTEGER DEFAULT 0
            )
        ''')
        self.ldb_connection.commit()

    async def update_user_xp(self, user_id, xp, new_level):
        # Update user's XP in the leveling database
        self.ldb_cursor.execute('''
            INSERT INTO user_xp (user_id, xp)
            VALUES (%s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET xp = user_xp.xp + EXCLUDED.xp
        ''', (user_id, xp))
        self.ldb_connection.commit()
        await self.update_level(user_id, new_level)

    async def get_level(self, user_id):
        # Retrieve the previous level from the database
        self.ldb_cursor.execute('''
            SELECT level FROM user_levels WHERE user_id = %s
        ''', (user_id,))
        level_row = self.ldb_cursor.fetchone()
        prev_level = level_row[0] if level_row else 0
        return prev_level

    async def update_level(self, guild_id, user_id, level):
    # Retrieve user's XP from the database
        self.ldb_cursor.execute('SELECT xp FROM user_xp WHERE user_id = %s', (user_id,))
        row = self.ldb_cursor.fetchone()
        if row:
            xp = row[0]
            # Calculate the new level based on the user's XP (your logic may vary)
            new_level = xp // 10  # For example, level up every 100 XP
            # Update the user's level in the database
            self.ldb_cursor.execute('''
                INSERT INTO user_levels (user_id, level)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET level = EXCLUDED.level
            ''', (user_id, new_level))
            self.ldb_connection.commit()
            # Send level-up message if applicable
            await self.send_level_up_message(user_id, new_level)

    async def send_level_up_message(self, user_id, level):
    # Fetch the level-up channel ID from the database
        self.ldb_cursor.execute('SELECT channel_id FROM levelup_channels WHERE guild_id = %s', (guild_id,))
        row = self.ldb_cursor.fetchone()
        if row:
            channel_id = row[0]
            # Get the channel object using the channel ID
            channel = self.bot.get_channel(channel_id)
            if channel:
                # Send the level-up message to the designated channel
                await channel.send(f"Congratulations <@{user_id}>! You've reached level {level}!")
        else:
            # No level-up channel defined for the guild
            print(f"No level-up channel defined for guild {guild_id}.")


    @commands.Cog.listener()
    async def on_message(self, message):
        # Award 1 XP per message
        if not message.author.bot:  # Check if the message is not from a bot
            await self.update_user_xp(message.author.id, 1)

    @commands.command()
    @is_staff()
    async def toggle(self, ctx):
        guild_id = ctx.guild.id
        top_roles = await self.get_top_roles(guild_id)
        
        # Check if the user invoking the command has any of the staff roles
        if any(role in [r.id for r in ctx.author.roles] for role in top_roles):
            # User has staff roles
            # Toggle leveling system in the current server
            self.ldb_cursor.execute('SELECT enabled FROM leveling_enabled WHERE guild_id = %s', (guild_id,))
            row = self.ldb_cursor.fetchone()
            if row:
                enabled = not row[0]
                self.ldb_cursor.execute('UPDATE leveling_enabled SET enabled = %s WHERE guild_id = %s', (enabled, guild_id))
            else:
                enabled = True
                self.ldb_cursor.execute('INSERT INTO leveling_enabled (guild_id, enabled) VALUES (%s, %s)', (guild_id, enabled))
            self.ldb_connection.commit()
            await ctx.send(f"Leveling system {'enabled' if enabled else 'disabled'}.")
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def view_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        level = await self.get_level(user.id)
        await ctx.send(f"{user.display_name} is at level {level}.")

    @commands.command()
    @is_staff()
    async def set_levelup_channel(self, ctx, channel: discord.TextChannel):
        # Check if the user invoking the command has any of the staff roles
        top_roles = await self.get_top_roles(ctx.guild.id)
        if any(role in [r.id for r in ctx.author.roles] for role in top_roles):
            # User has staff roles, proceed with setting the level up channel
            self.ldb_cursor.execute('''
                INSERT INTO levelup_channels (guild_id, channel_id)
                VALUES (%s, %s)
                ON CONFLICT (guild_id)
                DO UPDATE SET channel_id = EXCLUDED.channel_id
            ''', (ctx.guild.id, channel.id))
            self.ldb_connection.commit()
            await ctx.send(f"Level up messages will now be sent in {channel.mention}.")
        else:
            # User does not have staff roles, deny the command
            await ctx.send("You do not have permission to set the level up channel.")

#New
    @commands.Cog.listener()
    async def on_message(self, message):
        # Check if the message is not sent by a bot to avoid counting bot messages
        if not message.author.bot:
            # Call your method to update user XP by 1
            await self.update_user_xp(message.author.id, 1)

def setup(bot):
    bot.add_cog(levelModule(bot))
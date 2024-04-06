import os
import discord
from discord.ext import commands
import datetime
import pytz
import random
import sqlite3
from config import member_module
import psycopg2
import traceback

MeDB_URL = os.getenv('MeDB_URL')
MDB_URL = os.getenv('MDB_URL')
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

async def update_welcome_channel_data_type():
    try:
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)

        # Create a cursor object
        cur = conn.cursor()

        # Alter the data type of the welcome_channel_id column to BIGINT
        cur.execute("""
            ALTER TABLE server_settings
            ALTER COLUMN welcome_channel_id TYPE BIGINT;
        """)

        # Commit the changes to the database
        conn.commit()
        print("Data type of welcome_channel_id column updated successfully.")
    except psycopg2.Error as e:
        print("Error updating data type:", e)
        conn.rollback()  # Rollback the transaction in case of an error
        
update_welcome_channel_data_type()



# Modify the create_database function to include error handling
def create_database():
    try:
        # Retrieve the database URL from the environment variable
        database_url = MeDB_URL

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)

        # Create a cursor object
        cur = conn.cursor()

        # Execute the SQL command to create the server_settings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS server_settings (
                guild_id BIGINT PRIMARY KEY,
                welcome_channel_id BIGINT,
                dm_enabled INTEGER,
                custom_thumbnail_url TEXT,
                custom_image_url TEXT,
                use_embed INTEGER
            )
        """)

        # Commit the changes to the database
        conn.commit()
    except psycopg2.Error as e:
        print("Error creating database:", e)
        traceback.print_exc()  # Print traceback for debugging purposes
        conn.rollback()  # Rollback the transaction in case of an error
    finally:
        # Close the cursor and the connection
        if cur:
            cur.close()
        if conn:
            conn.close()


# Modify the save_server_settings function to include error handling
def save_server_settings(self):
    try:
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Clear the existing data in the table
        cursor.execute("DELETE FROM server_settings")

        # Iterate over all guilds the bot is part of and save their settings
        for guild in self.bot.guilds:
            welcome_channel_id = getattr(guild, 'welcome_channel_id', None)
            dm_enabled = int(self.dm_enabled)  # Convert bool to integer for storage
            use_embed = int(self.use_embed)    # Convert bool to integer for storage

            # Insert the server settings into the database
            cursor.execute("""
                INSERT INTO server_settings (guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (guild.id, welcome_channel_id, dm_enabled, self.custom_thumbnail_url, self.custom_image_url, use_embed))

        conn.commit()
    except psycopg2.Error as e:
        print("Error saving server settings:", e)
        traceback.print_exc()  # Print traceback for debugging purposes
        conn.rollback()  # Rollback the transaction in case of an error
    finally:
        # Close the cursor and the connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def is_owner_or_admin():
    async def predicate(ctx):
        if ctx.guild is None:
            return False

        if ctx.author == ctx.guild.owner or ctx.author.guild_permissions.administrator:
            return True

        return False
    return commands.check(predicate)


class memberCommandInfo():
    catname = "Server Commands"
    catnumber = 2

MEMBER_MODULE_COMMANDS = [
    {"name": "setwc", "brief": "Set the channel for welcome & goodbye messages."},
    {"name": "setdm", "brief": "Enable or disable DMs for welcome messages."},
    {"name": "setthumbnail", "brief": "Set custom thumbnail URL for welcome messages."},
    {"name": "setimage", "brief": "Set custom image URL for welcome messages."},
    {"name": "setembed", "brief": "Toggle using embeds for welcome messages."},
    {"name": "welsets", "brief": "Show the current welcome settings."}
]

class memberModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_enabled = False
        self.custom_thumbnail_url = None
        self.custom_image_url = None
        self.use_embed = True
        self.load_server_settings()

    def load_server_settings(self):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Fetch the server settings from the database
        cursor.execute("SELECT guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed FROM server_settings")
        rows = cursor.fetchall()

        # Store the fetched data in instance variables
        for row in rows:
            guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed = row
            self.dm_enabled = dm_enabled
            self.custom_thumbnail_url = custom_thumbnail_url
            self.custom_image_url = custom_image_url
            self.use_embed = bool(use_embed)

            # Update the welcome channel for the guild
            if welcome_channel_id is not None:
                self.bot.get_guild(guild_id).welcome_channel_id = welcome_channel_id

        conn.close()

    def save_server_settings(self):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Clear the existing data in the table
        cursor.execute("DELETE FROM server_settings")

        # Iterate over all guilds the bot is part of and save their settings
        for guild in self.bot.guilds:
            welcome_channel_id = getattr(guild, 'welcome_channel_id', None)
            dm_enabled = int(self.dm_enabled)  # Convert bool to integer for storage
            use_embed = int(self.use_embed)    # Convert bool to integer for storage

            # Insert the server settings into the database
            cursor.execute("""
                INSERT INTO server_settings (guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (guild.id, welcome_channel_id, dm_enabled, self.custom_thumbnail_url, self.custom_image_url, use_embed))

        conn.commit()
        conn.close()

    def log_to_database(self, guild_id, log_message):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Insert the log message into the member_logs table
        cursor.execute("""
            INSERT INTO member_logs (guild_id, log_message, log_time)
            VALUES (%s, %s, %s)
        """, (guild_id, log_message, datetime.now()))

        conn.commit()
        conn.close()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            log_message = "User {} changed display name from {} to {}".format(str(after), before.display_name, after.display_name)
            self.log_to_database(after.guild.id, log_message)

        elif before.roles != after.roles:
            log_message = "User {}'s roles changed from {} to {}".format(str(after), before.roles, after.roles)
            self.log_to_database(after.guild.id, log_message)

    def cog_unload(self):
        # Save server settings when the cog is unloaded (bot shutdown)
        self.save_server_settings()

    async def get_welcome_channel_id(self, guild_id):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Fetch the welcome channel ID from the database
        cursor.execute("SELECT welcome_channel_id FROM server_settings WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()

        conn.close()
        return row[0] if row else None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcomemsgs = ('Enjoy your stay!', 'Did you bring the party with you?', 'We hope you brought pizza.', 'Why hello there!')
        welcomemsg = random.choice(welcomemsgs)

        welcome_channel_id = await self.get_welcome_channel_id(member.guild.id)

        if welcome_channel_id:
            welcome_channel = self.bot.get_channel(welcome_channel_id)

            if not self.dm_enabled:
                if self.use_embed:
                    embed = discord.Embed(title=f"Welcome to {member.guild.name} {member.name}!",
                                          description=welcomemsg,
                                          color=member.guild.me.color)

                    if self.custom_thumbnail_url:
                        embed.set_thumbnail(url=self.custom_thumbnail_url)

                    await welcome_channel.send(embed=embed)
                else:
                    await welcome_channel.send(f"Welcome to {member.guild.name} {member.mention}! {welcomemsg}")
            else:
                await member.send(f"Welcome to {member.guild.name}! {welcomemsg}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        goodbyemsgs = ('We`re gonna miss you!', 'Goodbye!', 'Why are you running?')
        goodbyemsg = random.choice(goodbyemsgs)

        welcome_channel_id = await self.get_welcome_channel_id(member.guild.id)

        if welcome_channel_id:
            welcome_channel = self.bot.get_channel(welcome_channel_id)
            await welcome_channel.send(f"{goodbyemsg} {member.mention}!")
            
    async def update_server_setting(self, guild_id, setting_name, setting_value):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Update the specific server setting in the database
        cursor.execute(f"""
            UPDATE server_settings
            SET {setting_name} = %s
            WHERE guild_id = %s;
        """, (setting_value, guild_id))
    
        conn.commit()
        conn.close()

    @commands.command(brief="Set the channel for welcome & goodbye messages.", name="setwc")
    @is_staff()
    async def setwc(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            await self.update_server_setting(ctx.guild.id, 'welcome_channel_id', None)
            await ctx.send("Welcome channel has been reset.")
        else:
            await self.update_server_setting(ctx.guild.id, 'welcome_channel_id', channel.id)
            await ctx.send(f"Welcome channel has been set to {channel.mention}.")

    @commands.command(brief="Enable or disable DMs for welcome messages.", name="setdm")
    @is_staff()
    async def setdm(self, ctx, state: bool):
        await self.update_server_setting(ctx.guild.id, 'dm_enabled', state)
        await ctx.send(f"DM for welcome messages has been {'enabled' if state else 'disabled'}.")

    @commands.command(brief="Set custom thumbnail URL for welcome messages.", name="setthumbnail")
    @is_staff()
    async def setthumbnail(self, ctx, thumbnail_url: str = None):
        await self.update_server_setting(ctx.guild.id, 'custom_thumbnail_url', thumbnail_url)
        await ctx.send(f"Custom thumbnail URL has been {'reset' if thumbnail_url is None else 'set to ' + thumbnail_url}.")

    @commands.command(brief="Set custom image URL for welcome messages.", name="setimage")
    @is_staff()
    async def setimage(self, ctx, image_url: str = None):
        await self.update_server_setting(ctx.guild.id, 'custom_image_url', image_url)
        await ctx.send(f"Custom image URL has been {'reset' if image_url is None else 'set to ' + image_url}.")

    @commands.command(brief="Toggle using embeds for welcome messages.", name="setembed")
    @is_staff()
    async def setembed(self, ctx, state: bool):
        await self.update_server_setting(ctx.guild.id, 'use_embed', state)
        await ctx.send(f"Using embeds for welcome messages has been {'enabled' if state else 'disabled'}.")

    @commands.command(brief="Show the current welcome settings.", name="welsets")
    async def welsets(self, ctx):
        # Retrieve the database URL from the environment variable
        database_url = os.getenv('MeDB_URL')

        # Establish a connection to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Fetch the server settings from the database
        cursor.execute("SELECT welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed FROM server_settings WHERE guild_id = %s", (ctx.guild.id,))
        row = cursor.fetchone()

        if row:
            welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed = row
            welcome_channel_mention = ctx.guild.get_channel(welcome_channel_id).mention if welcome_channel_id else "Not set"
            dm_status = "Enabled" if dm_enabled else "Disabled"
            thumbnail_url = custom_thumbnail_url if custom_thumbnail_url else "Not set"
            image_url = custom_image_url if custom_image_url else "Not set"
            embed_status = "Enabled" if use_embed else "Disabled"
        else:
            welcome_channel_mention = "Not set"
            dm_status = "Disabled"
            thumbnail_url = "Not set"
            image_url = "Not set"
            embed_status = "Disabled"

        embed = discord.Embed(title="Current Welcome Settings", color=ctx.author.color)
        embed.add_field(name="Welcome Channel", value=welcome_channel_mention, inline=False)
        embed.add_field(name="DM for Welcome Messages", value=dm_status, inline=False)
        embed.add_field(name="Custom Thumbnail URL", value=thumbnail_url, inline=False)
        embed.add_field(name="Custom Image URL", value=image_url, inline=False)
        embed.add_field(name="Use Embeds for Welcome Messages", value=embed_status, inline=False)

        await ctx.send(embed=embed)

        conn.close()

def setup(bot):
    bot.add_cog(memberModule(bot))
    

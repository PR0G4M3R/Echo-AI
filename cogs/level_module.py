import discord
from discord.ext import commands
import sqlite3
import os

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
        self.conn = sqlite3.connect('level_data.db')
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create tables if they don't exist
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_xp (
                                user_id INTEGER PRIMARY KEY,
                                xp INTEGER
                              )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS levelup_channels (
                                guild_id INTEGER PRIMARY KEY,
                                channel_id INTEGER
                              )''')
        self.conn.commit()

    async def update_user_xp(self, user_id, xp):
        # Update user's XP
        self.cursor.execute('''INSERT OR REPLACE INTO user_xp (user_id, xp) VALUES (?, ?)''', (user_id, xp))
        self.conn.commit()

    async def get_level(self, user_id):
    # Retrieve the previous level from the database
        self.cursor.execute('''SELECT level FROM user_levels WHERE user_id = ?''', (user_id,))
        level_row = self.cursor.fetchone()
        prev_level = level_row[0] if level_row else 0
        return prev_level

    async def update_level(self, user_id, new_level):
        # Update the user's level in the database
        self.cursor.execute('''INSERT OR REPLACE INTO user_levels (user_id, level) VALUES (?, ?)''', (user_id, new_level))
        self.conn.commit()

    async def send_level_up_message(self, user_id, level):
        # Send level-up message to the designated channel
        # Implement this method as per your requirement

     @commands.Cog.listener()
     async def on_message(self, message):
        # Award 1 XP per message
        await self.update_user_xp(message.author.id, 1)

    def get_staff_roles(self, guild_id):
        # Read staff roles from the moderation log file for the given guild_id
        staff_roles = []
        # Use an absolute path for better reliability
        log_file_path = os.path.join('/app', 'logs', 'moderation_log.txt')
        with open(log_file_path, 'r') as file:
            for line in file:
                if line.startswith("Assigned roles:"):
                    # Roles are listed after this line
                    for role_line in file:
                        if not role_line.strip():
                            # End of roles section
                            break
                        # Extract role ID from the line and add it to staff_roles
                        role_id = int(role_line.split('(')[-1].split(')')[0])
                        staff_roles.append(role_id)
        return staff_roles

    @commands.command()
    async def toggle(self, ctx):
        guild_id = ctx.guild.id
        staff_roles = self.get_staff_roles(guild_id)
        
        # Check if the user invoking the command has any of the staff roles
        if any(role in [r.id for r in ctx.author.roles] for role in staff_roles):
            # User has staff roles
            # Toggle leveling system in the current server
            enabled_servers[ctx.guild.id] = not enabled_servers.get(ctx.guild.id, True)
            await ctx.send(f"Leveling system {'enabled' if enabled_servers[ctx.guild.id] else 'disabled'}.")
            pass
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def view_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        level = await self.get_level(user.id)
        await ctx.send(f"{user.display_name} is at level {level}.")
        return

    @commands.command()
    async def set_levelup_channel(self, ctx, channel: discord.TextChannel):
        # Set the channel where level-up messages will be sent
        levelup_channels[ctx.guild.id] = channel.id
        await ctx.send(f"Level-up messages will now be sent to {channel.mention}.")

        self.cursor.execute('''INSERT OR REPLACE INTO levelup_channels (guild_id, channel_id) VALUES (?, ?)''', (ctx.guild.id, channel.id))
        self.conn.commit()

def setup(bot):
    bot.add_cog(levelModule(bot))


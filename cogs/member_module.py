import os
import discord
from discord.ext import commands
import datetime
import pytz
import random
import sqlite3
from config import member_module

date_today_PST = datetime.datetime.now(pytz.timezone('UTC'))
date_str = date_today_PST.strftime("%m/%d/%Y")
time_str = date_today_PST.strftime("%H:%M:%S")

def create_database():
    conn = sqlite3.connect("server_settings.db")
    cursor = conn.cursor()

    # Create the table to store server settings if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel_id INTEGER,
            dm_enabled INTEGER,
            custom_thumbnail_url TEXT,
            custom_image_url TEXT,
            use_embed INTEGER
        )
    """)

    conn.commit()
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
        self.welcome_channels = {}  # Dictionary to store welcome channel IDs for each server
        self.dm_enabled = False
        self.custom_thumbnail_url = None
        self.custom_image_url = None
        self.use_embed = True
        self.load_server_settings()

    def load_server_settings(self):
        conn = sqlite3.connect("server_settings.db")
        cursor = conn.cursor()

        cursor.execute("SELECT guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed FROM server_settings")
        rows = cursor.fetchall()

        for row in rows:
            guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed = row
            self.welcome_channels[guild_id] = welcome_channel_id
            self.dm_enabled = dm_enabled
            self.custom_thumbnail_url = custom_thumbnail_url
            self.custom_image_url = custom_image_url
            self.use_embed = bool(use_embed)

        conn.close()

    def save_server_settings(self):
        conn = sqlite3.connect("server_settings.db")
        cursor = conn.cursor()

        # Clear the existing data in the table
        cursor.execute("DELETE FROM server_settings")

        # Save the current server settings
        for guild_id, welcome_channel_id in self.welcome_channels.items():
            dm_enabled = int(self.dm_enabled)  # Convert bool to integer for storage
            use_embed = int(self.use_embed)    # Convert bool to integer for storage

            cursor.execute("""
                INSERT INTO server_settings (guild_id, welcome_channel_id, dm_enabled, custom_thumbnail_url, custom_image_url, use_embed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, welcome_channel_id, dm_enabled, self.custom_thumbnail_url, self.custom_image_url, use_embed))

        conn.commit()
        conn.close()

    def cog_unload(self):
        # Save server settings when the cog is unloaded (bot shutdown)
        self.save_server_settings()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if member_module:
            if before.display_name != after.display_name:
                file = open('logs/member_log.txt', 'a')
                file.write(f'{date_str}, {time_str}\n')
                file.write("User {} changed display name from {} to {}\n".format(str(after), before.display_name, after.display_name))
                file.close()

            elif before.roles != after.roles:
                file = open('logs/member_log.txt', 'a')
                file.write(f'{date_str}, {time_str}\n')
                file.write("User {}'s roles changed from {} to {}\n".format(str(after), before.roles, after.roles))
                file.close()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcomemsgs = ('Enjoy your stay!', 'Did you bring the party with you?', 'We hope you brought pizza.', 'Why hello there!')
        welcomemsg = random.choice(welcomemsgs)
        goodbyemsgs = ('We`re gonna miss you!', 'Goodbye!', 'Why are you running?')
        goodbyemsg = random.choice(goodbyemsgs)

        welcome_channel_id = self.welcome_channels.get(member.guild.id)

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

        welcome_channel_id = self.welcome_channels.get(member.guild.id)

        if welcome_channel_id:
            welcome_channel = self.bot.get_channel(welcome_channel_id)
            await welcome_channel.send(f"{goodbyemsg} {member.mention}!")

    @commands.command(brief="Set the channel for welcome & goodbye messages.", name="setwc")
    @is_owner_or_admin()
    async def setwc(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            self.welcome_channels.pop(ctx.guild.id, None)
            await ctx.send("Welcome channel has been reset.")
        else:
            self.welcome_channels[ctx.guild.id] = channel.id
            await ctx.send(f"Welcome channel has been set to {channel.mention}.")

        # Save the server settings after changing the welcome channel
        self.save_server_settings()

    @commands.command(brief="Enable or disable DMs for welcome messages.", name="setdm")
    @is_owner_or_admin()
    async def setdm(self, ctx, state: bool):
        self.dm_enabled = state
        await ctx.send(f"DM for welcome messages has been {'enabled' if state else 'disabled'}.")

        # Save the server settings after changing the DM state
        self.save_server_settings()

    @commands.command(brief="Set custom thumbnail URL for welcome messages.", name="setthumbnail")
    @is_owner_or_admin()
    async def setthumbnail(self, ctx, thumbnail_url: str = None):
        self.custom_thumbnail_url = thumbnail_url
        await ctx.send(f"Custom thumbnail URL has been set to {thumbnail_url}.")

        # Save the server settings after changing the thumbnail URL
        self.save_server_settings()

    @commands.command(brief="Set custom image URL for welcome messages.", name="setimage")
    @is_owner_or_admin()
    async def setimage(self, ctx, image_url: str = None):
        self.custom_image_url = image_url
        await ctx.send(f"Custom image URL has been set to {image_url}.")

        # Save the server settings after changing the image URL
        self.save_server_settings()

    @commands.command(brief="Toggle using embeds for welcome messages.", name="setembed")
    @is_owner_or_admin()
    async def setembed(self, ctx, state: bool):
        self.use_embed = state
        await ctx.send(f"Using embeds for welcome messages has been {'enabled' if state else 'disabled'}.")

        # Save the server settings after changing the embed state
        self.save_server_settings()

    @commands.command(brief="Show the current welcome settings.", name="welsets")
    async def welsets(self, ctx):
        welcome_channel_id = self.welcome_channels.get(ctx.guild.id)
        welcome_channel_mention = ctx.guild.get_channel(welcome_channel_id).mention if welcome_channel_id else "Not set"
        dm_status = "Enabled" if self.dm_enabled else "Disabled"
        thumbnail_url = self.custom_thumbnail_url if self.custom_thumbnail_url else "Not set"
        image_url = self.custom_image_url if self.custom_image_url else "Not set"
        embed_status = "Enabled" if self.use_embed else "Disabled"

        embed = discord.Embed(title="Current Welcome Settings", color=ctx.author.color)
        embed.add_field(name="Welcome Channel", value=welcome_channel_mention, inline=False)
        embed.add_field(name="DM for Welcome Messages", value=dm_status, inline=False)
        embed.add_field(name="Custom Thumbnail URL", value=thumbnail_url, inline=False)
        embed.add_field(name="Custom Image URL", value=image_url, inline=False)
        embed.add_field(name="Use Embeds for Welcome Messages", value=embed_status, inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(memberModule(bot))

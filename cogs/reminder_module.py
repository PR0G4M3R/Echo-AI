import discord
from discord.ext import commands
import datetime
import pytz
import sqlite3
import asyncio

class commandInfo():
    catname = "Reminders"
    catnumber = 4
 
class reminderModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_conn = sqlite3.connect('reminders.db')
        self.init_db()
 
    def init_db(self):
        c = self.db_conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                user_id INTEGER,
                time TEXT,
                is_repeating INTEGER,
                message TEXT
            )
        ''')
        self.db_conn.commit()
 
    @commands.command(name='remind', brief='Make a reminder.', extras={"category": "Reminder Commands"})
    async def _remind(self, ctx, time, is_repeating, *, message):
        user_id = ctx.author.id

        if is_repeating.lower() == 'true':
            repeating = 1
        else:
            repeating = 0

        try:
            reminder_time = datetime.datetime.strptime(time, '%I:%M%p')
        except ValueError:
            await ctx.send("Invalid time format. Please use HH:MMAM/PM format, e.g., 12:46PM")
            return

        if reminder_time.strftime('%p') == 'PM':
            reminder_time = reminder_time.replace(hour=reminder_time.hour + 12)

        now = datetime.datetime.now(pytz.timezone('UTC'))
        reminder_time_utc = pytz.timezone('UTC').localize(reminder_time.replace(year=now.year, month=now.month, day=now.day))

        if reminder_time_utc <= now:
            await ctx.send("Invalid reminder time. Please provide a future time.")
            return

        c = self.db_conn.cursor()
        c.execute('''
            INSERT INTO reminders (user_id, time, is_repeating, message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, reminder_time_utc.strftime('%Y-%m-%d %H:%M:%S.%f%z'), repeating, message))

        self.db_conn.commit()
        await ctx.send('Reminder set.')

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.reminder_loop())

    async def reminder_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.datetime.now(pytz.timezone('UTC'))
 
            c = self.db_conn.cursor()
            c.execute('SELECT * FROM reminders WHERE time <= ?', (str(now),))
 
            rows = c.fetchall()
            for row in rows:
                user_id, _, _, message = row
                user = self.bot.get_user(user_id)
 
                await user.send('Reminder: {}'.format(message))
 
                c.execute('DELETE FROM reminders WHERE user_id = ? AND message = ?', (user_id, message))
                self.db_conn.commit()
 
            await asyncio.sleep(60)  # Check for reminders every 60 seconds
 
    @commands.command(brief='View reminders.', name="reminders", extras={"category": "Reminder Commands"})
    async def reminders(self, ctx):
        user_id = ctx.author.id
        c = self.db_conn.cursor()
        c.execute('SELECT time, is_repeating, message FROM reminders WHERE user_id = ?', (user_id,))
        rows = c.fetchall()

        if not rows:
            await ctx.send('You have no reminders.')
            return

        embed = discord.Embed(title='Your Reminders', colour=ctx.author.colour)
        for row in rows:
            time_str, is_repeating, message = row
            try:
                time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f%z')
            except ValueError:
                try:
                    time = datetime.datetime.strptime(time_str, '%I:%M%p')
                except ValueError:
                    await ctx.send(f'Invalid time format: {time_str}')
                    return

            embed.add_field(name='Time', value=str(time), inline=False)
            embed.add_field(name='Repeating', value='Yes' if is_repeating else 'No', inline=False)
            embed.add_field(name='Message', value=message, inline=False)

        await ctx.send(embed=embed)

    @commands.command(brief='Remove a reminder.', name="RemoveRem", extras={"category": "Reminder Commands"})
    async def _remove(self, ctx, *, message):
        user_id = ctx.author.id
        c = self.db_conn.cursor()
        c.execute('DELETE FROM reminders WHERE user_id = ? AND message = ?', (user_id, message))
        self.db_conn.commit()
        await ctx.send('Reminder removed.')

    @commands.command(brief='Edit your reminders.', name="EditRem", extras={"category": "Reminder Commands"})
    async def _edit(self, ctx, time, is_repeating, *, message):
        user_id = ctx.author.id
        c = self.db_conn.cursor()
        c.execute('UPDATE reminders SET time = ?, is_repeating = ? WHERE user_id = ? AND message = ?', (time, is_repeating, user_id, message))
        self.db_conn.commit()
        await ctx.send('Reminder edited.')

def setup(bot):
    bot.add_cog(reminderModule(bot))

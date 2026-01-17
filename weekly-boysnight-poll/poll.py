import discord
from discord.ext import commands, tasks
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Intents are required for the bot to interact with the server
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
CHANNEL_ID = os.getenv("CHANNEL_ID")
POLL_TIME = datetime.time(hour=9, minute=0)  # 09:00 AM


@tasks.loop(time=POLL_TIME)
async def weekly_poll():
    # Check if today is Wednesday (0=Mon, 1=Tue, 2=Wed...)
    if datetime.datetime.now().weekday() == 2:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🎮 Wednesday Gaming Poll",
                description="Are we playing games tonight?",
                color=discord.Color.blue(),
            )
            message = await channel.send(embed=embed)

            # Add reactions for quick voting
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            await message.add_reaction("⏰")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    # Start the background task
    if not weekly_poll.is_running():
        weekly_poll.start()


BOT_TOKEN = os.getenv("BOT_TOKEN")
bot.run(BOT_TOKEN)

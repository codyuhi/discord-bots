import discord
from discord.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import os
import sys
from dotenv import load_dotenv

# Ensure logs are flushed to Docker immediately
os.environ["PYTHONUNBUFFERED"] = "1"

load_dotenv()

# 1. SETUP
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. SAFE CONFIG LOAD
try:
    UTAH_TZ = ZoneInfo("America/Denver")
    POLL_TIME = datetime.time(hour=9, minute=0, tzinfo=UTAH_TZ)

    TOKEN = os.getenv("BOT_TOKEN")
    raw_channel_id = os.getenv("CHANNEL_ID")

    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing from environment.")
    if not raw_channel_id:
        raise ValueError("CHANNEL_ID is missing from environment.")

    CHANNEL_ID = int(raw_channel_id)
except Exception as e:
    print(f"CRITICAL CONFIG ERROR: {e}")
    sys.exit(1)


async def send_embed_poll():
    """Sends the wide-format RSVP card"""
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"ERROR: Bot cannot see channel {CHANNEL_ID}")
        return False

    # Create the Wide Embed
    embed = discord.Embed(
        title="🎮   Boys Night   🎮",
        description="It's Wednesday, my dudes.\n**Who's gaming tonight?**\n\n──────────────────────────",
        color=0x5865F2,
        timestamp=datetime.datetime.now(UTAH_TZ),
    )

    # Full-width fields (inline=False) to prevent 'mushed' look
    embed.add_field(name="✅  Yes", value="I plan to join", inline=False)
    embed.add_field(
        name="⏰  Maybe/late",
        value="Unsure if I can join, or may be late",
        inline=False,
    )
    embed.add_field(name="❌  No", value="Unable to join", inline=False)

    embed.set_footer(text="Select your status by clicking an emoji below")

    try:
        # Pinging outside the embed ensures notifications are sent
        message = await channel.send(content="", embed=embed)

        await message.add_reaction("✅")
        await message.add_reaction("⏰")
        await message.add_reaction("❌")
        return True
    except Exception as e:
        print(f"ERROR sending message: {e}")
        return False


# 3. SCHEDULER
@tasks.loop(time=POLL_TIME)
async def weekly_poll_task():
    # 2 = Wednesday
    if datetime.datetime.now(UTAH_TZ).weekday() == 2:
        print("Triggering scheduled poll...")
        await send_embed_poll()


# 4. COMMANDS
@bot.command(name="testpoll")
async def test_poll(ctx):
    print("Manual trigger: !testpoll received")
    success = await send_embed_poll()
    if not success:
        await ctx.send("❌ Error: Check bot logs for details.")


@bot.event
async def on_ready():
    print(f"--- Bot successfully connected as {bot.user} ---")
    print(f"Targeting Channel ID: {CHANNEL_ID}")
    if not weekly_poll_task.is_running():
        weekly_poll_task.start()


# 5. START
if __name__ == "__main__":
    bot.run(TOKEN)

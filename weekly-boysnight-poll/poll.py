import discord
from discord.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import os
import sys
import re
import random
from dotenv import load_dotenv

# Ensure logs are flushed to Docker immediately
os.environ["PYTHONUNBUFFERED"] = "1"

# Configure SSL certificate path if certifi is available (helps local macOS/Docker environments)
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

load_dotenv()

# Pool of rotating lighthearted greetings for the weekly poll
POLL_MESSAGES = [
    "It's Thursday, my dudes.",
    "Thursday night gaming vibes. Who's in?",
    "Grab a drink, hop on Discord, let's play some games.",
    "The weekend is close, but gaming starts tonight.",
    "Time for some casual games and good times.",
    "Headsets on, ready to unwind tonight?",
    "Thursday check-in: who's hanging out and gaming?",
    "Good vibes and gaming tonight. Who's around?",
    "Booting up for Thursday night. Who's joining the squad?",
    "Time to chill and play some games tonight.",
    "Another Thursday, another gaming session with the boys.",
    "Rounds, laughs, and good times ahead. Who's in?",
    "Taking a break from the week to game tonight.",
    "Snacks ready, games loaded. Who's pulling up tonight?",
    "Who's ready for some Thursday night gaming?",
    "Dropping into the server tonight for some fun.",
    "Casual gaming session tonight—who's available?",
    "Unwinding with some games tonight. Who's in?",
    "Thursday game night is here! Who's hopping on?",
]

# 1. SETUP
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. SAFE CONFIG LOAD
try:
    UTAH_TZ = ZoneInfo("America/Denver")
    POLL_TIME = datetime.time(hour=9, minute=0, tzinfo=UTAH_TZ)

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing from environment.")

    # Parse channel IDs from various possible environment variables
    raw_channel_inputs = [
        os.getenv("CHANNEL_IDS", ""),
        os.getenv("CHANNEL_ID", ""),
        os.getenv("TEST_CHANNEL_ID", ""),
        os.getenv("SNAKECODE_TEST_CHANNEL_ID", ""),
        os.getenv("SHOOTY_BOIS_CHANNEL_ID", ""),
    ]

    channel_id_list = []
    for raw in raw_channel_inputs:
        if raw:
            for item in raw.split(","):
                item_str = item.strip()
                if item_str.isdigit():
                    val = int(item_str)
                    if val not in channel_id_list:
                        channel_id_list.append(val)

    if not channel_id_list:
        raise ValueError("No valid CHANNEL_ID, CHANNEL_IDS, or TEST_CHANNEL_ID found in environment.")

    CHANNEL_IDS = channel_id_list
except Exception as e:
    print(f"CRITICAL CONFIG ERROR: {e}")
    sys.exit(1)


# 3. STATELESS LOGIC
class PersistentRSVPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Required for persistence

    def parse_names(self, field_value):
        """Extracts names from field value"""
        if not field_value:
            return []
        names = re.findall(r"•\s+(.+)", field_value)
        if not names:
            names = [line.strip() for line in field_value.split("\n") if line.strip()]
        return names

    async def update_card(self, interaction: discord.Interaction, target_label):
        """Scrapes existing state from the Discord message and dynamically updates responder groups"""
        embed = interaction.message.embeds[0]

        yes_list = []
        maybe_list = []
        no_list = []

        # Scrape dynamically from existing fields
        for field in embed.fields:
            if "✅" in field.name or "Yes" in field.name:
                yes_list = self.parse_names(field.value)
            elif "⏰" in field.name or "Maybe" in field.name:
                maybe_list = self.parse_names(field.value)
            elif "❌" in field.name or "No" in field.name:
                no_list = self.parse_names(field.value)

        mapping = {"Yes": yes_list, "Maybe": maybe_list, "No": no_list}
        user_name = interaction.user.display_name

        # SRE Debug Logging
        print(f"DEBUG: Click by {user_name} for {target_label}.")

        # Remove user from all lists to allow switching votes
        for lst in mapping.values():
            while user_name in lst:
                lst.remove(user_name)

        # Add to the new list
        mapping[target_label].append(user_name)

        # Build Updated Embed preserving original header message
        new_embed = discord.Embed(
            title=embed.title or "🎮   Boys Night   🎮",
            description=embed.description,
            color=0x5865F2,
        )

        # Only add groups that have active votes
        if yes_list:
            new_embed.add_field(
                name="✅  Yes",
                value="\n".join([f"• {n}" for n in yes_list]),
                inline=False,
            )
        if maybe_list:
            new_embed.add_field(
                name="⏰  Maybe/late",
                value="\n".join([f"• {n}" for n in maybe_list]),
                inline=False,
            )
        if no_list:
            new_embed.add_field(
                name="❌  No",
                value="\n".join([f"• {n}" for n in no_list]),
                inline=False,
            )

        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(
        label="Yes", style=discord.ButtonStyle.success, emoji="✅", custom_id="bn_yes"
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.update_card(interaction, "Yes")

    @discord.ui.button(
        label="Maybe",
        style=discord.ButtonStyle.secondary,
        emoji="⏰",
        custom_id="bn_maybe",
    )
    async def tentative(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.update_card(interaction, "Maybe")

    @discord.ui.button(
        label="No", style=discord.ButtonStyle.danger, emoji="❌", custom_id="bn_no"
    )
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.update_card(interaction, "No")


def create_initial_embed(custom_message=None):
    """Builds the starting card with a randomized intro greeting and no empty responder groups"""
    greeting = custom_message or random.choice(POLL_MESSAGES)
    embed = discord.Embed(
        title="🎮   Boys Night   🎮",
        description=f"{greeting}\n**Who's gaming tonight?**",
        color=0x5865F2,
    )
    return embed


async def send_poll(target_channel=None):
    """Sends the poll embed with RSVP view. If target_channel is provided, sends to that channel; otherwise sends to all configured channels."""
    if target_channel:
        try:
            await target_channel.send(embed=create_initial_embed(), view=PersistentRSVPView())
            channel_name = getattr(target_channel, "name", "unknown")
            print(f"SUCCESS: Poll sent to channel #{channel_name} ({target_channel.id})")
            return True
        except Exception as e:
            print(f"ERROR: Failed to send poll to channel {target_channel.id}: {e}")
            return False

    all_success = True
    for ch_id in CHANNEL_IDS:
        channel = bot.get_channel(ch_id)
        if not channel:
            try:
                channel = await bot.fetch_channel(ch_id)
            except Exception as e:
                print(f"CRITICAL: Failed to fetch channel {ch_id}: {e}")
                all_success = False
                continue

        try:
            await channel.send(embed=create_initial_embed(), view=PersistentRSVPView())
            channel_name = getattr(channel, "name", "unknown")
            print(f"SUCCESS: Poll sent to #{channel_name} ({ch_id})")
        except Exception as e:
            print(f"ERROR: Failed to send poll to {ch_id}: {e}")
            all_success = False
    return all_success


# 4. SCHEDULER & COMMANDS


@bot.check
async def globally_restrict_to_channel(ctx):
    """Prevents the bot from processing commands outside its assigned channels."""
    return ctx.channel.id in CHANNEL_IDS


@tasks.loop(time=POLL_TIME)
async def weekly_poll_task():
    if datetime.datetime.now(UTAH_TZ).weekday() == 3:  # Thursday
        print("Triggering scheduled Thursday poll...")
        await send_poll()


@bot.command(name="sendpoll", aliases=["testpoll"])
async def send_poll_command(ctx):
    channel_name = getattr(ctx.channel, "name", "unknown")
    print(f"Manual trigger: !sendpoll received from {ctx.author} in #{channel_name} ({ctx.channel.id})")
    await send_poll(target_channel=ctx.channel)


@bot.event
async def on_ready():
    # Re-register view for old message persistence
    bot.add_view(PersistentRSVPView())
    print("--- Bot Online ---")
    print(f"Logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"Connected Guilds: {[guild.name for guild in bot.guilds]}")
    print(f"Targeting Channel IDs: {CHANNEL_IDS}")
    if not weekly_poll_task.is_running():
        weekly_poll_task.start()


if __name__ == "__main__":
    bot.run(TOKEN)

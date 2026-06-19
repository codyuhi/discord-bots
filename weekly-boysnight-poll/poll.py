import discord
from discord.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import os
import sys
import re
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


# 3. STATELESS LOGIC
class PersistentRSVPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Required for persistence

    def parse_names(self, field_value):
        """Extracts names from the bulleted list; ignores placeholder text"""
        if any(x in field_value for x in ["I plan to join", "Unsure", "Unable"]):
            return []
        return re.findall(r"•\s+(.+)", field_value)

    async def update_card(self, interaction: discord.Interaction, target_label):
        """Scrapes existing state from the Discord message and updates it"""
        embed = interaction.message.embeds[0]

        # Parse current names from fields
        yes_list = self.parse_names(embed.fields[0].value)
        maybe_list = self.parse_names(embed.fields[1].value)
        no_list = self.parse_names(embed.fields[2].value)

        mapping = {"Yes": yes_list, "Maybe": maybe_list, "No": no_list}
        user_name = interaction.user.display_name

        # SRE Debug Logging
        print(f"DEBUG: Click by {user_name} for {target_label}.")

        # Remove user from all lists to allow 'switching' votes
        for lst in mapping.values():
            if user_name in lst:
                lst.remove(user_name)

        # Add to the new list
        mapping[target_label].append(user_name)

        # Build Updated Embed
        new_embed = discord.Embed(
            title="🎮   Boys Night   🎮",
            description="It's Thursday, my dudes.\n**Who's gaming tonight?**\n\n──────────────────────────",
            color=0x5865F2,
            timestamp=datetime.datetime.now(UTAH_TZ),
        )

        new_embed.add_field(
            name="✅  Yes",
            value="\n".join([f"• {n}" for n in yes_list]) or "I plan to join",
            inline=False,
        )
        new_embed.add_field(
            name="⏰  Maybe/late",
            value="\n".join([f"• {n}" for n in maybe_list])
            or "Unsure if I can join, or may be late",
            inline=False,
        )
        new_embed.add_field(
            name="❌  No",
            value="\n".join([f"• {n}" for n in no_list]) or "Unable to join",
            inline=False,
        )
        new_embed.set_footer(text="Select your status by clicking a button below")

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


def create_initial_embed():
    """Builds the starting card with your preferred wording"""
    embed = discord.Embed(
        title="🎮   Boys Night   🎮",
        description="It's Thursday, my dudes.\n**Who's gaming tonight?**\n\n──────────────────────────",
        color=0x5865F2,
        timestamp=datetime.datetime.now(UTAH_TZ),
    )
    embed.add_field(name="✅  Yes", value="I plan to join", inline=False)
    embed.add_field(
        name="⏰  Maybe/late",
        value="Unsure if I can join, or may be late",
        inline=False,
    )
    embed.add_field(name="❌  No", value="Unable to join", inline=False)
    embed.set_footer(text="Select your status by clicking a button below")
    return embed


async def send_poll():
    # Cache lookup with API fallback
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"CRITICAL: Failed to fetch channel {CHANNEL_ID}: {e}")
            return False

    try:
        await channel.send(embed=create_initial_embed(), view=PersistentRSVPView())
        print(f"SUCCESS: Poll sent to {CHANNEL_ID}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send poll: {e}")
    return False


# 4. SCHEDULER & COMMANDS


@bot.check
async def globally_restrict_to_channel(ctx):
    """Prevents the bot from processing commands outside its assigned channel env var."""
    return ctx.channel.id == CHANNEL_ID


@tasks.loop(time=POLL_TIME)
async def weekly_poll_task():
    if datetime.datetime.now(UTAH_TZ).weekday() == 3:  # Thursday
        print("Triggering scheduled Thursday poll...")
        await send_poll()


@bot.command(name="testpoll")
async def test_poll(ctx):
    print(f"Manual trigger: !testpoll received from {ctx.author}")
    await send_poll()


@bot.event
async def on_ready():
    # Re-register view for old message persistence
    bot.add_view(PersistentRSVPView())
    print(f"--- Bot Online ---")
    print(f"Targeting Channel ID: {CHANNEL_ID}")
    if not weekly_poll_task.is_running():
        weekly_poll_task.start()


if __name__ == "__main__":
    bot.run(TOKEN)

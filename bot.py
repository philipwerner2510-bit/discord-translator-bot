import os
import discord
from discord.ext import commands
from discord import app_commands
from googletrans import Translator

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator = Translator()

# Store allowed channels and user languages in memory
allowed_channels = set()
user_languages = {}

# --- Slash command for setting channels (Admin only) ---
class ChannelSelect(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in channels
        ]
        super().__init__(placeholder="Select channels to enable the bot in...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        global allowed_channels
        selected_ids = {int(v) for v in self.values}
        allowed_channels = selected_ids
        await interaction.response.send_message(f"✅ Enabled translation in {len(selected_ids)} channels.", ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, channels):
        super().__init__()
        self.add_item(ChannelSelect(channels))

@bot.tree.command(name="setchannel", description="Select which channels the bot should monitor (Admin only).")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    channels = [ch for ch in interaction.guild.text_channels]
    view = ChannelSelectView(channels)
    await interaction.response.send_message("Select channels:", view=view, ephemeral=True)

@setchannel.error
async def setchannel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need admin rights to use this command.", ephemeral=True)

# --- Slash command to set user language ---
@bot.tree.command(name="setlanguage", description="Set your preferred translation language (e.g. en, de, fr, ja)")
async def setlanguage(interaction: discord.Interaction, language: str):
    user_languages[interaction.user.id] = language.lower()
    await interaction.response.send_message(f"✅ Your translation language has been set to `{language}`.", ephemeral=True)

# --- Reaction listener ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) == "🔃":
        if reaction.message.channel.id not in allowed_channels:
            return

        try:
            # Remove user’s reaction
            await reaction.remove(user)
        except:
            pass

        # Get user language (default English)
        target_lang = user_languages.get(user.id, "en")

        text = reaction.message.content
        if not text:
            return

        try:
            translated = translator.translate(text, dest=target_lang)
            dm = await user.create_dm()
            await dm.send(f"**Translated ({target_lang})**:\n{translated.text}")
        except Exception as e:
            print(f"Error translating: {e}")
            try:
                await user.send("⚠️ Translation failed. Please try again later.")
            except:
                pass

# --- On ready ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced ({len(synced)})")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# --- Run the bot ---
bot.run(os.getenv("BOT_TOKEN"))

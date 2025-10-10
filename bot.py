import os
import discord
from discord.ext import commands
from discord import app_commands
from googletrans import Translator

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator = Translator()

# Memory storage
allowed_channels = set()
user_languages = {}

# --- Slash command for setting channels (Admin only) ---
class ChannelSelect(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in channels
        ]
        super().__init__(
            placeholder="✅ Select channels to enable the bot in",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        global allowed_channels
        selected = {int(v) for v in self.values}
        allowed_channels = selected
        names = [f"#{interaction.guild.get_channel(cid).name}" for cid in selected]
        await interaction.response.edit_message(
            content="✅ Enabled translation in:\n" + "\n".join(names),
            view=None
        )

class ChannelSelectView(discord.ui.View):
    def __init__(self, channels):
        super().__init__(timeout=60)
        self.add_item(ChannelSelect(channels))

@bot.tree.command(name="setchannel", description="Select which channels the bot will monitor (Admin only).")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    channels = [ch for ch in interaction.guild.text_channels]
    view = ChannelSelectView(channels)
    await interaction.response.send_message(
        "Select channels to enable translation:", view=view, ephemeral=True
    )

@setchannel.error
async def setchannel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need admin rights to use this command.", ephemeral=True)

# --- Slash command to set preferred language ---
@bot.tree.command(name="setlanguage", description="Set your preferred translation language (e.g. en, de, fr, ja)")
async def setlanguage(interaction: discord.Interaction, language: str):
    user_languages[interaction.user.id] = language.lower()
    await interaction.response.send_message(
        f"✅ Your preferred language is now `{language}`.",
        ephemeral=True
    )

# --- Add 🔃 automatically to messages in allowed channels ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id in allowed_channels:
        try:
            await message.add_reaction("🔃")
        except Exception as e:
            print(f"Couldn't react: {e}")
    await bot.process_commands(message)

# --- Handle 🔃 reactions ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if str(reaction.emoji) != "🔃":
        return
    if reaction.message.channel.id not in allowed_channels:
        return

    try:
        await reaction.remove(user)
    except:
        pass

    text = reaction.message.content
    if not text:
        return

    target_lang = user_languages.get(user.id, "en")

    try:
        translated = translator.translate(text, dest=target_lang)
        dm = await user.create_dm()
        await dm.send(
            f"💬 **Original:**\n{text}\n\n🌍 **Translated ({target_lang}):**\n{translated.text}"
        )
    except Exception as e:
        print(f"Error translating: {e}")
        try:
            await user.send("⚠️ Translation failed. Please try again.")
        except:
            pass

# --- Startup ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync failed: {e}")

bot.run(os.getenv("BOT_TOKEN"))

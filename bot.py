import discord
from discord.ext import commands
from discord import app_commands
from deep_translator import GoogleTranslator
import os

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store user languages and active channels
user_languages = {}
active_channels = set()

# 🌍 Command: Choose which channels translation should work in
@bot.tree.command(name="setchannels", description="Select which channels the translator should work in.")
@app_commands.describe(channels="Comma-separated list of channels (by name) where translation is active.")
async def set_channels(interaction: discord.Interaction, channels: str):
    channel_names = [ch.strip() for ch in channels.split(",")]
    added = []
    for name in channel_names:
        for ch in interaction.guild.text_channels:
            if ch.name == name:
                active_channels.add(ch.id)
                added.append(ch.name)
    if added:
        await interaction.response.send_message(
            f"✅ Translator active in: {', '.join(added)}", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "⚠️ No matching channels found. Make sure to use exact channel names.", ephemeral=True
        )

# 🌐 Command: Let user pick their target language
@bot.tree.command(name="setlanguage", description="Choose your language for automatic translations.")
@app_commands.describe(language="Enter your target language (e.g. english, german, arabic, etc.)")
async def set_language(interaction: discord.Interaction, language: str):
    user_languages[interaction.user.id] = language.lower()
    await interaction.response.send_message(f"✅ Your language has been set to **{language.title()}**.", ephemeral=True)

# 🆕 Automatically react to every message in active channels
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id in active_channels:
        try:
            await message.add_reaction("🔃")
        except discord.Forbidden:
            print(f"⚠️ Missing permission to add reaction in {message.channel}")
    await bot.process_commands(message)

# 🔃 Reaction event: translate message when user reacts
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.emoji != "🔃":
        return
    if reaction.message.channel.id not in active_channels:
        return
    if user.id not in user_languages:
        try:
            await user.send("⚙️ Please set your language first using `/setlanguage`.")
        except:
            pass
        try:
            await reaction.remove(user)
        except:
            pass
        return

    target_lang = user_languages[user.id]
    original_text = reaction.message.content

    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(original_text)
        await reaction.message.reply(translated, mention_author=False, silent=True)
    except Exception as e:
        try:
            await user.send(f"❌ Translation error: {e}")
        except:
            pass

    # Remove the user's reaction to keep message clean
    try:
        await reaction.remove(user)
    except:
        pass

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} — ready for translations!")

bot.run(os.getenv("BOT_TOKEN"))

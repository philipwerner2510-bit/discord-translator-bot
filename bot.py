import os
import discord
from discord.ext import commands
from googletrans import Translator

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)
translator = Translator()

# Store user language preferences
user_languages = {}

# Store which channels the bot should monitor
active_channels = set()

# ----------------------------
# Slash command: set language
# ----------------------------
@bot.tree.command(name="language", description="Set your preferred translation language (e.g., en, de, ar, fa)")
async def language(interaction: discord.Interaction, lang: str):
    user_languages[interaction.user.id] = lang.lower()
    await interaction.response.send_message(
        f"✅ Your language has been set to **{lang.upper()}**",
        ephemeral=True
    )

# ----------------------------
# Slash command: select channels
# ----------------------------
@bot.tree.command(name="setchannels", description="Select which channels the bot should translate in")
async def setchannels(interaction: discord.Interaction):
    options = [
        discord.SelectOption(label=channel.name, value=str(channel.id))
        for channel in interaction.guild.text_channels
    ]

    class ChannelSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Select channels...", min_values=1, max_values=len(options), options=options)

        async def callback(self, inner_interaction: discord.Interaction):
            selected_ids = [int(v) for v in self.values]
            active_channels.clear()
            active_channels.update(selected_ids)
            await inner_interaction.response.send_message(
                f"✅ Bot will now translate only in: {', '.join([f'<#{cid}>' for cid in selected_ids])}",
                ephemeral=True
            )

    view = discord.ui.View()
    view.add_item(ChannelSelect())
    await interaction.response.send_message("Select which channels should support translation 🔃:", view=view, ephemeral=True)

# ----------------------------
# On new messages — add 🔃 reaction
# ----------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id not in active_channels:
        return
    try:
        await message.add_reaction("🔃")
    except discord.errors.Forbidden:
        print("Bot does not have permission to add reactions.")

# ----------------------------
# On reaction add — translate and DM
# ----------------------------
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if str(reaction.emoji) != "🔃":
        return
    if reaction.message.channel.id not in active_channels:
        return

    # Remove the user's reaction so only bot's remains
    try:
        await reaction.remove(user)
    except discord.errors.Forbidden:
        pass

    # Ensure user has set language
    if user.id not in user_languages:
        await user.send("⚠️ Please set your language first using `/language [code]` (example: `/language en`).")
        return

    target_lang = user_languages[user.id]
    text = reaction.message.content.strip()
    if not text:
        await user.send("⚠️ This message has no text to translate.")
        return

    try:
        translated = translator.translate(text, dest=target_lang)
        await user.send(translated.text)
    except Exception as e:
        print(e)
        await user.send("❌ Translation failed. Try again later.")

# ----------------------------
# Startup event
# ----------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(e)

bot.run(os.getenv("BOT_TOKEN"))

import discord
from discord import app_commands
from discord.ext import commands
from googletrans import Translator
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator = Translator()

# Store guild-specific translation channels
translation_channels = {}

# Load saved channels from a file (optional for persistence)
if os.path.exists("channels.txt"):
    with open("channels.txt", "r") as f:
        for line in f:
            guild_id, channel_id = line.strip().split(":")
            translation_channels[int(guild_id)] = int(channel_id)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")


@bot.tree.command(name="setchannel", description="Set the translation reaction channel (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    guild = interaction.guild
    channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]

    # Create selection menu
    options = [
        discord.SelectOption(label=c.name, description=f"Set {c.name} for translations", value=str(c.id))
        for c in channels[:25]
    ]

    select = discord.ui.Select(placeholder="Select a translation channel", options=options)

    async def select_callback(interaction2: discord.Interaction):
        selected_channel_id = int(select.values[0])
        translation_channels[guild.id] = selected_channel_id

        # Save it persistently
        with open("channels.txt", "w") as f:
            for gid, cid in translation_channels.items():
                f.write(f"{gid}:{cid}\n")

        await interaction2.response.send_message(
            f"✅ Translation channel set to <#{selected_channel_id}>", ephemeral=True
        )

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message("Select a channel for translation reactions:", view=view, ephemeral=True)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Only react in designated channel
    channel_id = translation_channels.get(message.guild.id)
    if channel_id and message.channel.id == channel_id:
        await message.add_reaction("🔃")


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) == "🔃":
        msg = reaction.message
        await reaction.remove(user)  # remove user’s reaction immediately

        # Ask user privately which language they want
        try:
            await user.send("🌐 Please reply with a language code (e.g., `en` for English, `fr` for French, `de` for German):")
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)

            reply = await bot.wait_for("message", check=check, timeout=60)
            lang = reply.content.strip().lower()

            translated = translator.translate(msg.content, dest=lang)
            await user.send(
                f"✅ **Translated Message:**\n\n{translated.text}\n\n🌍 Language: {lang}"
            )

        except Exception as e:
            await user.send(f"❌ Error during translation: {e}")


@setchannel.error
async def setchannel_error(interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "🚫 You need **Administrator** permissions to use this command.", ephemeral=True
        )

bot.run(TOKEN)

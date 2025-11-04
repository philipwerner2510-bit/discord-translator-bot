# cogs/welcome.py
import discord
from discord.ext import commands

BOT_COLOR = 0xDE002A

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_welcome_embed(self, guild: discord.Guild):
        e = discord.Embed(
            title="👋 Thanks for adding Demon Translator!",
            description=(
                "Get instant translations with just a reaction.\n\n"
                "**Quick Setup**\n"
                "1️⃣ Choose translation channels → `/channelselection`\n"
                "2️⃣ Set server language → `/defaultlang <lang>`\n"
                "3️⃣ (Optional) Set reaction emoji → `/emote <emoji>`\n\n"
                "Users can set their own language with `/setmylang`, and translate any text with `/translate`.\n\n"
                "ℹ️ Use `/help` anytime for the full command menu.\n"
                "🔁 The bot falls back to 🔁 if your custom emoji can’t be used."
            ),
            color=BOT_COLOR
        )
        e.set_footer(text="Demon Translator by Polarix#1954")
        return e

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = self.build_welcome_embed(guild)
        # Send to first text channel where the bot can speak
        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages:
                try:
                    await ch.send(embed=embed)
                    break
                except Exception:
                    continue

async def setup(bot):
    await bot.add_cog(Welcome(bot))
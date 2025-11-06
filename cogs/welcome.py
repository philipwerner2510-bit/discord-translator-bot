# cogs/welcome.py
import discord
from discord.ext import commands
from utils.brand import COLOR, WELCOME_TITLE, footer, Z_HAPPY, SERVER_BANNER_URL, AVATAR_URL

WELCOME_DESC = (
    "Thanks for inviting **Zephyra**!\n\n"
    "Quick start:\n"
    "1) `/channelselection` — pick channels for reaction-based translation\n"
    "2) `/defaultlang <code>` — set your server language (autocomplete)\n"
    "3) `/emote <emoji>` — set the translate reaction\n"
    "4) `/guide` — post a how-to for your members"
)

class Welcome(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = discord.Embed(title=f"{Z_HAPPY} {WELCOME_TITLE}", description=WELCOME_DESC, color=COLOR)
        embed.set_footer(text=footer())
        if SERVER_BANNER_URL:
            embed.set_image(url=SERVER_BANNER_URL)
        if AVATAR_URL:
            embed.set_thumbnail(url=AVATAR_URL)

        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages and perms.embed_links:
                try:
                    await ch.send(embed=embed); break
                except Exception:
                    pass

async def setup(bot): await bot.add_cog(Welcome(bot))

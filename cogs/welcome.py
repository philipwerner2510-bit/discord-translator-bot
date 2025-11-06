import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME, SERVER_BANNER_URL, AVATAR_URL
from utils.roles import role_ladder, gradient_color
# ... inside the cog class:

async def _ensure_role(self, guild: discord.Guild, name: str, color_int: int):
    # find existing (case-insensitive)
    for r in guild.roles:
        if r.name.lower() == name.lower():
            # sync color if changed
            if r.colour.value != color_int:
                try:
                    await r.edit(colour=discord.Colour(color_int), reason="Sync role ladder color")
                except Exception:
                    pass
            return r
    # create if missing
    try:
        return await guild.create_role(
            name=name,
            colour=discord.Colour(color_int),
            reason="Create role ladder (auto)",
            mentionable=False,
            hoist=False,
        )
    except Exception:
        return None

async def ensure_role_ladder(self, guild: discord.Guild):
    tiers = role_ladder()
    for t in tiers:
        await self._ensure_role(guild, t["name"], t["color"])

# call from on_guild_join
@commands.Cog.listener()
async def on_guild_join(self, guild: discord.Guild):
    # your existing welcome flow...
    try:
        await self.ensure_role_ladder(guild)
    except Exception:
        pass

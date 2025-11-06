# cogs/welcome.py
from __future__ import annotations
import discord
from discord.ext import commands
from utils.roles import role_ladder

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Try to create the 10-level role ladder when bot joins a new server.
        # Requires Manage Roles. Fail silently if missing perms.
        try:
            existing = {r.name for r in guild.roles}
            for spec in role_ladder():
                if spec["name"] in existing:
                    continue
                await guild.create_role(
                    name=spec["name"],
                    colour=discord.Colour(spec["color"]),
                    reason="Initialize level role ladder (1–100 in 10-step bands)"
                )
        except Exception:
            # Ignore if no permission or role position issues; admin can run /admin roles later
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))

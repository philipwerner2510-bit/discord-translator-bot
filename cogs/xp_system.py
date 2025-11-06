# cogs/xp_system.py (imports)
from utils.roles import role_ladder, best_role_for_level

# inside the cog class:

async def sync_level_role(self, member: discord.Member, level: int):
    guild = member.guild
    tiers = role_ladder()
    # Map by lower name for easy checks
    ladder_names = {t["name"].lower() for t in tiers}
    target = best_role_for_level(level)["name"].lower()

    # Ensure all roles exist (if someone deleted them)
    for t in tiers:
        try:
            await self.bot.get_cog("Welcome")._ensure_role(guild, t["name"], t["color"])
        except Exception:
            pass

    # Refresh role objects
    role_by_name = {r.name.lower(): r for r in guild.roles}
    add_role = role_by_name.get(target)

    # Remove all ladder roles except the target
    to_remove = [r for r in member.roles if r.name.lower() in ladder_names and r.name.lower() != target]
    for r in to_remove:
        try:
            await member.remove_roles(r, reason="Level ladder sync")
        except Exception:
            pass

    # Add target if missing
    if add_role and add_role not in member.roles:
        try:
            await member.add_roles(add_role, reason=f"Reached level {level}")
        except Exception:
            pass

# wherever you handle XP gain/level up:
# After computing new level (and detecting level change), call:
# await self.sync_level_role(member, new_level)

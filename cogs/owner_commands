import os
import io
import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 762267166031609858  # Polarix
BOT_COLOR = 0xDE002A

def _is_owner(itx: discord.Interaction) -> bool:
    return bool(itx.user and itx.user.id == OWNER_ID)

class OwnerOnly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="reload", description="(Owner) Reload all cogs.")
    async def reload(self, interaction: discord.Interaction):
        if not _is_owner(interaction):
            return await interaction.response.send_message("Nope.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        reloaded, failed = [], []

        # Reload every loaded extension safely
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception as e:
                failed.append(f"{ext}: {type(e).__name__} — {e}")

        msg = "✅ **Reloaded**\n" + ("\n".join(reloaded) if reloaded else "—")
        if failed:
            msg += "\n\n❌ **Failed**\n" + "\n".join(failed)
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="backup", description="(Owner) Backup DB and DM it.")
    async def backup(self, interaction: discord.Interaction):
        if not _is_owner(interaction):
            return await interaction.response.send_message("Nope.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        db_path = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")
        try:
            with open(db_path, "rb") as f:
                buf = io.BytesIO(f.read())
            buf.seek(0)
            file = discord.File(buf, filename="bot_data.db")
            await interaction.user.send("Here is your DB backup:", file=file)
            await interaction.followup.send("✅ DM sent.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Backup failed: {e}", ephemeral=True)

    @app_commands.command(name="summonpolarix", description="(Owner) DM yourself a server invite button.")
    async def summonpolarix(self, interaction: discord.Interaction):
        if not _is_owner(interaction):
            return await interaction.response.send_message("Nope.", ephemeral=True)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Invite Demon Translator",
            url="https://discord.com/api/oauth2/authorize?client_id=1425590836800000170&permissions=2147483648&scope=bot%20applications.commands"
        ))
        try:
            await interaction.user.send("Here’s your quick invite button:", view=view)
            await interaction.response.send_message("✅ Sent to your DMs.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not DM you: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerOnly(bot))
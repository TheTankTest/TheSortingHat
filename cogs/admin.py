import discord
from discord import app_commands
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="refresh_commands", description="Force refresh all slash commands for this guild")
    async def refresh_commands(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
        await self.bot.tree.sync(guild=discord.Object(id=interaction.guild.id))
        await interaction.response.send_message(
            f"✅ Commands refreshed for guild: **{interaction.guild.name}**",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

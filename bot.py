import os
import asyncio
import logging
import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN,
    GUILD_ID,
    DEBUG,
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)  # Prefix unused; all commands are slash
logger = logging.getLogger("clan_bot")


async def load_cogs():
    # Load cogs explicitly so startup errors are clear
    for ext in (
        "cogs.applications",
        "cogs.points",
        "cogs.admin",
    ):
        try:
            await bot.load_extension(ext)
            logger.info(f"Loaded extension: {ext}")
        except Exception as e:
            logger.exception(f"Failed to load {ext}: {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Guild-scoped sync for fast iteration, else global sync
    try:
        if GUILD_ID:
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            logger.info(f"Slash commands synced to guild {GUILD_ID} ({len(synced)} commands)")
        else:
            synced = await bot.tree.sync()
            logger.info(f"Slash commands globally synced ({len(synced)} commands)")
    except Exception as e:
        logger.exception(f"Slash sync failed: {e}")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

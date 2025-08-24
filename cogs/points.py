from typing import List
import discord
from discord import app_commands
from discord.ext import commands

from utils.constants import normalize_account_type, API_BOSS_ORDER, get_boss_points
from utils.hiscores import fetch_csv_rows, extract_boss_kc, compute_points

class Points(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="points", description="Lookup KC → clan points via hiscores.")
    @app_commands.describe(username="Exact OSRS name", account_type="normal, ironman, hcim, uim, gim, ugim")
    async def points(self, interaction: discord.Interaction, username: str, account_type: str = "normal"):
        acct = normalize_account_type(account_type or "normal")
        if not acct:
            return await interaction.response.send_message(
                "Unknown account type. Try: normal, ironman, hcim, uim, gim, ugim", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        rows = await fetch_csv_rows(username, acct)
        if not rows:
            return await interaction.followup.send(
                f"Couldn't find hiscores for '{username}' on {acct}.", ephemeral=True
            )

        kc_map = extract_boss_kc(rows)
        boss_points = get_boss_points()
        total, breakdown = compute_points(kc_map, boss_points)
        if total == 0:
            return await interaction.followup.send(
                "No eligible boss killcounts detected for points.", ephemeral=True
            )

        lines = [f"- {b}: {kc} KC → {pts:.2f} pts" for b, kc, pts in breakdown]

        chunks: List[List[str]] = []
        current: List[str] = []
        current_len = 0
        for line in lines:
            add_len = len(line) + 1
            if current_len + add_len > 3500:  # margin
                chunks.append(current)
                current = [line]
                current_len = add_len
            else:
                current.append(line)
                current_len += add_len
        if current:
            chunks.append(current)

        embeds: List[discord.Embed] = []
        for idx, chunk in enumerate(chunks, start=1):
            title = f"{username} — {acct} hiscores"
            if len(chunks) > 1:
                title += f" (part {idx}/{len(chunks)})"
            emb = discord.Embed(
                title=title,
                description="\n".join(chunk),
                color=discord.Color.blurple()
            )
            if idx == 1:
                emb.add_field(name="Total Points", value=f"{total:.2f}", inline=False)
            embeds.append(emb)

        for emb in embeds:
            await interaction.followup.send(embed=emb, ephemeral=True)

    @app_commands.command(name="kc_debug", description="Developer: show raw tail rows to align boss order.")
    @app_commands.describe(username="OSRS username", account_type="Hiscores type (e.g., normal, ironman, ugim)")
    async def kc_debug(self, interaction: discord.Interaction, username: str, account_type: str = "normal"):
        await interaction.response.defer(ephemeral=True, thinking=True)
        acct = normalize_account_type(account_type) or "normal"
        rows = await fetch_csv_rows(username, acct)
        if not rows:
            return await interaction.followup.send("No rows returned (user not found?).", ephemeral=True)

        tail = rows[-len(API_BOSS_ORDER):]
        lines = []
        for i, r in enumerate(tail):
            rank = r[0] if len(r) > 0 else -1
            score = r[1] if len(r) > 1 else -1
            xp = r[2] if len(r) > 2 else -1
            name = API_BOSS_ORDER[i] if i < len(API_BOSS_ORDER) else "<UNMAPPED>"
            lines.append(f"{i:02d} | {name:<28} | rank={rank:<6} score/kc={score:<8} xp={xp:<8}")

        text = "Tail mapping (index_lite):\n" + "\n".join(lines)

        chunks: List[str] = []
        while text:
            chunks.append(text[:1900])
            text = text[1900:]
        for idx, chunk in enumerate(chunks, start=1):
            suffix = f" (part {idx}/{len(chunks)})" if len(chunks) > 1 else ""
            await interaction.followup.send(f"```text\n{chunk}\n```{suffix}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Points(bot))

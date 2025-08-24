from __future__ import annotations
from typing import Optional, List, Tuple
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    STAFF_CHANNEL_ID,
    MEMBER_ROLE_ID,
    VISITOR_ROLE_ID,
)
from utils.constants import ACCOUNT_TYPE_OPTIONS, normalize_account_type
from utils.constants import get_boss_points
from utils.hiscores import fetch_csv_rows, extract_boss_kc, compute_points
from utils.ranks import get_rank_name


APPLICATION_TYPE_OPTIONS = [
    ("visitor", "Visitor", "Visiting the clan"),
    ("member", "Clan Member", "Applying to join as member"),
]


def parse_alts(raw: str) -> List[str]:
    if not raw:
        return []
    seps = [",", "|", "\n", ";"]
    s = raw
    for sep in seps:
        s = s.replace(sep, ",")
    alts = [x.strip() for x in s.split(",") if x.strip()]
    # Deduplicate, preserve order
    seen = set()
    unique = []
    for a in alts:
        low = a.lower()
        if low not in seen:
            seen.add(low)
            unique.append(a)
    return unique


def build_nickname(main: str, alts_raw: str, limit: int = 32) -> str:
    alts = parse_alts(alts_raw)
    candidate = main
    for a in alts:
        next_candidate = f"{candidate} | {a}"
        if len(next_candidate) <= limit:
            candidate = next_candidate
        else:
            break
    return candidate


class AccountTypeSelect(discord.ui.Select):
    def __init__(self, requestor_id: int):
        self.requestor_id = requestor_id
        options = [
            discord.SelectOption(label=label, value=value, description=desc)
            for value, label, desc in ACCOUNT_TYPE_OPTIONS
        ]
        super().__init__(placeholder="Choose Account Type…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: ApplicationPrefaceView = self.view  # type: ignore
        if interaction.user.id != view.requestor_id:
            return await interaction.response.send_message("Only the original requester can use this.", ephemeral=True)
        view.selected_account_type = self.values[0]
        await interaction.response.defer()  # state updated silently


class ApplicationTypeSelect(discord.ui.Select):
    def __init__(self, requestor_id: int):
        self.requestor_id = requestor_id
        options = [
            discord.SelectOption(label=label, value=value, description=desc)
            for value, label, desc in APPLICATION_TYPE_OPTIONS
        ]
        super().__init__(placeholder="Visitor or Clan Member…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: ApplicationPrefaceView = self.view  # type: ignore
        if interaction.user.id != view.requestor_id:
            return await interaction.response.send_message("Only the original requester can use this.", ephemeral=True)
        view.selected_application_type = self.values[0]
        await interaction.response.defer()


class StartApplicationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Start Application", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: ApplicationPrefaceView = self.view  # type: ignore
        if interaction.user.id != view.requestor_id:
            return await interaction.response.send_message("Only the original requester can use this.", ephemeral=True)
        if not view.selected_account_type or not view.selected_application_type:
            return await interaction.response.send_message(
                "Please select both Account Type and Application Type first.", ephemeral=True
            )
        await interaction.response.send_modal(ApplicationModal(
            account_type=view.selected_account_type,
            application_type=view.selected_application_type
        ))


class ApplicationPrefaceView(discord.ui.View):
    def __init__(self, requestor_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.requestor_id = requestor_id
        self.selected_account_type: Optional[str] = None
        self.selected_application_type: Optional[str] = None
        self.add_item(AccountTypeSelect(requestor_id))
        self.add_item(ApplicationTypeSelect(requestor_id))
        self.add_item(StartApplicationButton())


class ApplicationDecisionView(discord.ui.View):
    def __init__(self, applicant_id: int, applicant_name: str):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_name = applicant_name

    async def _finalize(self, interaction: discord.Interaction, decision: str, color: discord.Color):
        msg = interaction.message
        if not msg or not msg.embeds:
            return await interaction.response.send_message("No embed found to update.", ephemeral=True)

        embed = msg.embeds[0]
        embed.color = color
        footer_text = (embed.footer.text or "").strip()
        decided_by = f"Decision: {decision} by {interaction.user} ({interaction.user.id})"
        embed.set_footer(text=f"{footer_text} • {decided_by}" if footer_text else decided_by)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

        if interaction.guild:
            try:
                member = interaction.guild.get_member(self.applicant_id)
                if member:
                    role = None
                    if "Member" in decision and MEMBER_ROLE_ID:
                        role = interaction.guild.get_role(MEMBER_ROLE_ID)
                    elif "Visitor" in decision and VISITOR_ROLE_ID:
                        role = interaction.guild.get_role(VISITOR_ROLE_ID)
                    if role:
                        await member.add_roles(role, reason="Accepted via clan application")
            except discord.Forbidden:
                pass
            except Exception:
                pass

        user = interaction.client.get_user(self.applicant_id)
        if user is None:
            try:
                user = await interaction.client.fetch_user(self.applicant_id)  # type: ignore
            except Exception:
                user = None
        if user:
            try:
                dm = discord.Embed(
                    title="Clan Application Update",
                    description=f"Your application for {self.applicant_name} has been reviewed.\nResult: {decision}",
                    color=color
                )
                await user.send(embed=dm)
            except Exception:
                pass

    @discord.ui.button(label="Accept as Clan Member", style=discord.ButtonStyle.green)
    async def accept_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finalize(interaction, "Accepted as Clan Member ✅", discord.Color.green())

    @discord.ui.button(label="Accept as Visitor", style=discord.ButtonStyle.blurple)
    async def accept_visitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finalize(interaction, "Accepted as Visitor ✅", discord.Color.blurple())

    @discord.ui.button(label="Decline Application", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finalize(interaction, "Declined ❌", discord.Color.red())

class ApplicationModal(discord.ui.Modal, title="Clan Application"):
    def __init__(self, account_type: str, application_type: str):
        super().__init__()
        self.account_type = account_type
        self.application_type = application_type

        self.osrs_name = discord.ui.TextInput(
            label="Old School RuneScape Name",
            placeholder="Type your OSRS name exactly",
            required=True,
            max_length=12,
        )
        self.firecape = discord.ui.TextInput(
            label="Do you have a Fire Cape?",
            placeholder="Yes / No",
            required=True,
            max_length=10,
        )
        self.infernal_cape = discord.ui.TextInput(
            label="Do you have an Infernal Cape?",
            placeholder="Yes / No",
            required=True,
            max_length=10,
        )
        self.alts = discord.ui.TextInput(
            label="Do you have any alts?",
            placeholder="List your alts (comma, newline, or | separated)",
            required=False,
            style=discord.TextStyle.long,
            max_length=200,
        )

        self.add_item(self.osrs_name)
        self.add_item(self.firecape)
        self.add_item(self.infernal_cape)
        self.add_item(self.alts)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            print(f"[DEBUG] Final modal submit from {interaction.user} ({interaction.user.id})")
            await interaction.response.defer(ephemeral=True, thinking=True)
            print("[DEBUG] Interaction deferred")

            rsn = str(self.osrs_name.value).strip()
            acct = self.account_type
            app_type_label = "Visitor" if self.application_type == "visitor" else "Clan Member"

            # hiscores + points calc
            print("[DEBUG] Fetching hiscores data…")
            rows = await fetch_csv_rows(rsn, acct)
            kc_map = extract_boss_kc(rows) if rows else {}
            boss_points = get_boss_points()
            total_points, breakdown = compute_points(kc_map, boss_points)
            rank_name = get_rank_name(total_points)

            # Build staff review embed
            embed = discord.Embed(title="New Clan Application", color=discord.Color.green())
            embed.add_field(name="OSRS Name", value=rsn or "—", inline=True)
            embed.add_field(name="Account Type", value=acct.replace("_", " ").title(), inline=True)
            embed.add_field(name="Application Type", value=app_type_label, inline=True)
            embed.add_field(name="Recommended Rank", value=rank_name, inline=True)
            embed.add_field(name="Fire Cape", value=self.firecape.value or "—", inline=True)
            embed.add_field(name="Infernal Cape", value=self.infernal_cape.value or "—", inline=True)

            if self.alts.value:
                alts_preview = ", ".join(parse_alts(self.alts.value))[:1024]
                embed.add_field(name="Alts", value=alts_preview or "—", inline=False)

            if rows:
                embed.add_field(name="Total Points", value=f"{total_points:.2f}", inline=False)
                if breakdown:
                    top = "\n".join(f"- {b}: {kc} KC → {pts:.2f} pts" for b, kc, pts in breakdown[:8])
                    embed.add_field(name="Top Contributors", value=top[:1024], inline=False)
            else:
                embed.add_field(name="Hiscores Lookup", value="User not found on selected hiscores.", inline=False)

            embed.set_footer(text=f"From {interaction.user} ({interaction.user.id})")

            # Send to staff channel
            staff_channel = interaction.client.get_channel(STAFF_CHANNEL_ID) if STAFF_CHANNEL_ID else None
            print(f"[DEBUG] STAFF_CHANNEL_ID={STAFF_CHANNEL_ID}, staff_channel={staff_channel}")
            decision_view = ApplicationDecisionView(applicant_id=interaction.user.id, applicant_name=rsn)

            if staff_channel:
                try:
                    await staff_channel.send(
                        content=f"<@{interaction.user.id}>",
                        embed=embed,
                        view=decision_view,
                        allowed_mentions=discord.AllowedMentions(users=True, roles=True)
                    )
                    ack = "✅ Application submitted! Staff and you have been notified."
                    print("[DEBUG] Posted to staff channel successfully")
                except Exception as e:
                    print("[ERROR] Failed to send to staff channel:", repr(e))
                    ack = "❌ Application saved, but staff notification failed."
            else:
                try:
                    await interaction.user.send(embed=embed)
                    ack = "✅ Application submitted! (Staff channel not set; sent you a DM copy.)"
                    print("[DEBUG] Sent application to user via DM")
                except Exception as e:
                    print("[ERROR] Failed to DM user:", repr(e))
                    ack = "✅ Application submitted! (Staff channel not set and DM failed.)"

            # Nickname update
            if interaction.guild:
                try:
                    member = interaction.guild.get_member(interaction.user.id)
                    if member:
                        nick = build_nickname(rsn, self.alts.value or "")
                        await member.edit(nick=nick, reason="Set by application submission (main + alts)")
                        print(f"[DEBUG] Updated nickname to {nick}")
                except discord.Forbidden:
                    print("[WARN] Missing permission to change nickname")
                except Exception as e:
                    print("[ERROR] Nickname update failed:", repr(e))

            try:
                await interaction.followup.send(ack, ephemeral=True)
                print("[DEBUG] Followup sent to applicant")
            except Exception as e:
                print("[ERROR] Failed to send followup:", repr(e))

        except Exception as outer_e:
            print("[FATAL] Exception in on_submit:", repr(outer_e))
            try:
                await interaction.followup.send(
                    "❌ Something went wrong submitting your application. Please try again later.",
                    ephemeral=True
                )
            except:
                pass



class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="apply", description="Submit a clan application with automatic points lookup")
    async def apply(self, interaction: discord.Interaction):
        view = ApplicationPrefaceView(requestor_id=interaction.user.id)
        await interaction.response.send_message(
            "Select your Account Type and Application Type, then click Start Application.",
            view=view,
            ephemeral=True
        )

    class ApplyHereButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Start Application", style=discord.ButtonStyle.success)

        async def callback(self, interaction: discord.Interaction):
            # When someone clicks the public button, start a fresh preface view tied to them
            preface_view = ApplicationPrefaceView(requestor_id=interaction.user.id)
            await interaction.response.send_message(
                "Select your Account Type and Application Type, then click Start Application.",
                view=preface_view,
                ephemeral=True
            )

    class ApplyHereView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(ApplyHereButton())

    @app_commands.command(name="send_apply_button", description="Send the public 'Apply Here' button embed")
    async def send_apply_button(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Clan Applications",
            description="Click the button below to begin your application.",
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=embed, view=ApplyHereView())
        await interaction.response.send_message("✅ Apply button posted.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Applications(bot))

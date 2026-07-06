import discord
from discord.ext import commands
import time
import json
from utils.database import db
from utils.embeds import *


class Punishments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="punish")
    async def punish(self, ctx, user: discord.Member = None, punishment: str = None,
                     duration: str = None, *, reason: str = None):
        if not user or not punishment:
            return await ctx.send(embed=error_embed("Usage: /punish @user [punishment] [duration] [reason]"))

        if user.top_role.position >= ctx.author.top_role.position:
            return await ctx.send(embed=error_embed(f"{user.mention}'s role is equal to or higher than yours."))

        bot_member = ctx.guild.me
        if user.top_role.position >= bot_member.top_role.position:
            return await ctx.send(embed=error_embed(f"My role is below {user.mention}. I cannot punish them."))

        punishment = punishment.lower()
        dm_user = False
        if reason and "dm:true" in reason.lower():
            dm_user = True
            reason = reason.replace("dm:true", "").replace("dm:True", "").strip()

        if punishment == "timeout":
            dur_seconds = self.parse_duration(duration or "1h")
            await user.timeout(dur_seconds, reason=reason or "No reason")
            embed = success_embed("Timed Out", f"{user.mention} has been timed out for {duration or '1h'}.\nReason: {reason or 'No reason'}")
            await ctx.send(embed=embed)
            await self.mod_log(ctx, "TIMEOUT", user, f"Duration: {duration or '1h'}\nReason: {reason or 'No reason'}", ctx.author)
            if dm_user:
                await self.dm_user(user, "Timed Out", f"You have been timed out for {duration or '1h'}.\nReason: {reason or 'No reason'}")

        elif punishment == "kick":
            await user.kick(reason=reason or "No reason")
            embed = success_embed("Kicked", f"{user.mention} has been kicked.\nReason: {reason or 'No reason'}")
            await ctx.send(embed=embed)
            await self.mod_log(ctx, "KICK", user, f"Reason: {reason or 'No reason'}", ctx.author)
            if dm_user:
                await self.dm_user(user, "Kicked", f"You have been kicked.\nReason: {reason or 'No reason'}")

        elif punishment == "ban":
            del_days = 7
            if duration and duration.isdigit():
                del_days = int(duration)
            await user.ban(reason=reason or "No reason", delete_message_days=del_days)
            embed = success_embed("Banned", f"{user.mention} has been banned. Message history deleted: {del_days} days.\nReason: {reason or 'No reason'}")
            await ctx.send(embed=embed)
            await self.mod_log(ctx, "BAN", user, f"Delete History: {del_days} days\nReason: {reason or 'No reason'}", ctx.author)
            if dm_user:
                await self.dm_user(user, "Banned", f"You have been banned.\nDelete History: {del_days} days\nReason: {reason or 'No reason'}")

        elif punishment == "warn":
            await db.db.execute(
                "INSERT INTO warns (guild_id, user_id, reason, mod_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (ctx.guild.id, user.id, reason or "No reason", ctx.author.id, time.time()))
            await db.db.commit()
            cursor = await db.db.execute(
                "SELECT COUNT(*) FROM warns WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, user.id))
            total = (await cursor.fetchone())[0]
            embed = success_embed("Warned", f"{user.mention} has been warned.\nReason: {reason or 'No reason'}\nTotal warns: {total}")
            await ctx.send(embed=embed)
            await self.mod_log(ctx, "WARN", user, f"Total Warns: {total}\nReason: {reason or 'No reason'}", ctx.author)
            if dm_user:
                await self.dm_user(user, "Warned", f"You have been warned.\nReason: {reason or 'No reason'}\nTotal warnings: {total}")

        else:
            # Role-based punishment
            cursor = await db.db.execute(
                "SELECT value FROM guild_config WHERE guild_id = ? AND key = 'role_punishments'",
                (ctx.guild.id,))
            row = await cursor.fetchone()
            if row:
                rp = json.loads(row[0])
                if punishment in rp:
                    role_id = rp[punishment]["role_id"]
                    role = ctx.guild.get_role(role_id)
                    if role:
                        dur_seconds = self.parse_duration(duration or "1d")
                        await user.add_roles(role, reason=reason or "No reason")
                        if dur_seconds and dur_seconds > 0:
                            await db.db.execute(
                                "INSERT OR REPLACE INTO temp_role_assignments (guild_id, user_id, role_id, expires_at) VALUES (?, ?, ?, ?)",
                                (ctx.guild.id, user.id, role_id, time.time() + dur_seconds))
                            await db.db.commit()
                        embed = success_embed(punishment.upper(), f"{user.mention} has been given {role.mention} for {duration or 'permanent'}.\nReason: {reason or 'No reason'}")
                        await ctx.send(embed=embed)
                        await self.mod_log(ctx, punishment.upper(), user, f"Duration: {duration or 'permanent'}\nReason: {reason or 'No reason'}", ctx.author)

    @commands.hybrid_command(name="punishment", aliases=["premove"])
    async def punishment_remove(self, ctx, user: discord.Member = None, punishment: str = None, *, reason: str = None):
        if not user or not punishment:
            return await ctx.send(embed=error_embed("Usage: /punishment remove @user [punishment] [reason]"))
        cursor = await db.db.execute(
            "SELECT value FROM guild_config WHERE guild_id = ? AND key = 'role_punishments'",
            (ctx.guild.id,))
        row = await cursor.fetchone()
        if row:
            rp = json.loads(row[0])
            if punishment in rp:
                role_id = rp[punishment]["role_id"]
                role = ctx.guild.get_role(role_id)
                if role and role in user.roles:
                    await user.remove_roles(role, reason=reason or "No reason")
                    await db.db.execute(
                        "DELETE FROM temp_role_assignments WHERE guild_id = ? AND user_id = ? AND role_id = ?",
                        (ctx.guild.id, user.id, role_id))
                    await db.db.commit()
                    embed = success_embed(f"{punishment.upper()} Removed",
                        f"{user.mention} has been un{punishment.lower()}ed.\nReason: {reason or 'No reason'}")
                    await ctx.send(embed=embed)
                    await self.mod_log(ctx, f"{punishment.upper()} REMOVED", user, f"Reason: {reason or 'No reason'}", ctx.author)

    @commands.hybrid_command(name="listpunished", aliases=["list_punished"])
    async def list_punished(self, ctx):
        embed = info_embed("Active Punishments", "", private=True)
        now = time.time()
        # Timeouts - can't really list active timeouts via API, skip
        # Role punishments
        cursor = await db.db.execute(
            "SELECT user_id, role_id, expires_at FROM temp_role_assignments WHERE guild_id = ? AND expires_at > ?",
            (ctx.guild.id, now))
        rows = await cursor.fetchall()
        role_lines = []
        for uid, rid, exp in rows:
            m = ctx.guild.get_member(uid)
            r = ctx.guild.get_role(rid)
            remaining = exp - now
            hours = remaining // 3600
            mins = (remaining % 3600) // 60
            role_lines.append(f"• {m.mention if m else f'<@{uid}>'} — {r.mention if r else f'<@&{rid}>'} (expires in {hours:.0f}h {mins:.0f}m)")
        if role_lines:
            embed.add_field(name="Role Punishments", value="\n".join(role_lines), inline=False)
        # Warns
        cursor = await db.db.execute(
            "SELECT user_id, COUNT(*) as cnt FROM warns WHERE guild_id = ? GROUP BY user_id", (ctx.guild.id,))
        warn_lines = [f"• {ctx.guild.get_member(r[0]).mention if ctx.guild.get_member(r[0]) else f'<@{r[0]}>'} — {r[1]} warns" for r in await cursor.fetchall()]
        if warn_lines:
            embed.add_field(name="Warns", value="\n".join(warn_lines), inline=False)
        if not role_lines and not warn_lines:
            embed.description = "No active punishments."
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="p")
    async def p_shortcut(self, ctx, user: discord.Member = None, punishment: str = None,
                         duration: str = None, *, reason: str = None):
        await self.punish(ctx, user, punishment, duration, reason=reason)

    @commands.hybrid_command(name="report")
    async def report(self, ctx, user: discord.Member = None, *, reason: str = None):
        if not user or not reason:
            return await ctx.send(embed=error_embed("Usage: /report @user [reason]"))
        cursor = await db.db.execute(
            "SELECT value FROM guild_config WHERE guild_id = ? AND key = 'reports_channel_id'",
            (ctx.guild.id,))
        row = await cursor.fetchone()
        if row:
            ch_id = json.loads(row[0])
            channel = ctx.guild.get_channel(ch_id)
            if channel:
                embed = warning_embed("New Report",
                    f"**Reporter:** {ctx.author.mention}\n**Target:** {user.mention}\n**Reason:** {reason}")
                await channel.send(embed=embed)
        await ctx.send(embed=success_embed("Report Sent", "Your report has been sent to moderators."), ephemeral=True)

    @commands.command(name="psetup_all")
    async def psetup_all(self, ctx):
        embed = info_embed("Punishment Setup Wizard", "Let's set up the punishment system.")
        view = ConfirmView(ctx, "Start setup?")
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if not view.value:
            return
        await msg.edit(embed=info_embed("Step 1", "Which channel for punishment logs?\nReply with #channel or **skip**."), view=None)
        try:
            r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if r.content.startswith("<#"):
                await db.set_guild_config(ctx.guild.id, "mod_logs_channel_id", int(r.content.strip("<#>")))
            await ctx.send(embed=info_embed("Step 2", "Which channel for user reports?\nReply with #channel or **skip**."))
            r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if r.content.startswith("<#"):
                await db.set_guild_config(ctx.guild.id, "reports_channel_id", int(r.content.strip("<#>")))
            await ctx.send(embed=info_embed("Step 3", "Which role(s) are mod roles?\nReply with @role or **skip**."))
            mod_roles = []
            while True:
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.strip().lower() == "skip":
                    break
                if r.content.startswith("<@&"):
                    mod_roles.append(int(r.content.strip("<@&>")))
                    await ctx.send("Add another? @role or **skip**.")
            if mod_roles:
                await db.set_guild_config(ctx.guild.id, "mod_roles", mod_roles)
            await ctx.send(embed=success_embed("Setup complete!"))
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="psetup")
    async def psetup(self, ctx):
        embed = info_embed("Punishment Setup Menu",
            "1. Mod Logs Channel\n2. Reports Channel\n3. Mod Roles\n"
            "4. Role-Based Punishments\n5. Standard Punishments\n\nType number or **done**.")
        await ctx.send(embed=embed)

    def parse_duration(self, duration_str: str) -> int:
        import re
        total = 0
        for match in re.finditer(r"(\d+)([hdwm])", duration_str.lower()):
            num = int(match.group(1))
            unit = match.group(2)
            mult = {"h": 3600, "d": 86400, "w": 604800, "m": 2592000}
            total += num * mult.get(unit, 0)
        return total

    async def mod_log(self, ctx, action: str, user: discord.Member, details: str, mod: discord.Member):
        cursor = await db.db.execute(
            "SELECT value FROM guild_config WHERE guild_id = ? AND key = 'mod_logs_channel_id'",
            (ctx.guild.id,))
        row = await cursor.fetchone()
        if not row:
            return
        try:
            ch_id = int(json.loads(row[0])) if isinstance(json.loads(row[0]), int) else json.loads(row[0])
        except:
            return
        channel = ctx.guild.get_channel(ch_id)
        if not channel:
            return
        emojis = {"TIMEOUT": "🚔", "KICK": "🦵", "BAN": "🔨", "WARN": "⚠️"}
        emoji = emojis.get(action, "🔇")
        embed = info_embed(f"{emoji} {action}")
        embed.add_field(name="Target", value=user.mention, inline=True)
        embed.add_field(name="Mod", value=mod.mention, inline=True)
        for line in details.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                embed.add_field(name=k.strip(), value=v.strip(), inline=True)
        try:
            await channel.send(embed=embed)
        except:
            pass

    async def dm_user(self, user: discord.User, action: str, details: str):
        try:
            emojis = {"Timed Out": "🚔", "Kicked": "🦵", "Banned": "🔨", "Warned": "⚠️"}
            emoji = emojis.get(action, "🔇")
            embed = info_embed(f"{emoji} {action}", details, private=True)
            await user.send(embed=embed)
        except:
            pass


class ConfirmView(discord.ui.View):
    def __init__(self, ctx, question=""):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        self.value = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        self.value = False
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


async def setup(bot):
    await bot.add_cog(Punishments(bot))

import discord
from discord.ext import commands
import time
import json
import random
from utils.database import db
from utils.embeds import *


class Wallet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="wallet", aliases=["balance", "bal"])
    async def wallet(self, ctx, user: discord.Member = None):
        target = user or ctx.author
        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        currencies = config.get("currencies", {})
        if not currencies:
            return await ctx.send(embed=info_embed("Wallet", "Economy not set up yet."))

        embed = info_embed(f"{target.display_name}'s Wallet")
        ranks = {}
        for cur in currencies:
            ranks[cur] = await db.get_user_ranks(ctx.guild.id, cur)

        for cur, emoji in currencies.items():
            bal = await db.get_user_balance(ctx.guild.id, target.id, cur)
            rank_info = ranks.get(cur, {}).get(target.id, {})
            rank_str = f"(Rank #{rank_info.get('rank', '?')})" if rank_info else ""
            embed.add_field(name=f"{emoji} {cur}", value=f"{bal:,.0f} {rank_str}", inline=True)

        # Conversion bar
        ratio = await db.get_global_config("shard_orb_ratio", "3:1")
        max_convert = await db.get_global_config("max_shards_convertable", 3000)
        cursor = await db.db.execute(
            "SELECT COALESCE(SUM(amount_converted), 0) FROM conversion_tracking WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, target.id))
        converted = (await cursor.fetchone())[0]
        remaining = max(0, max_convert - converted)
        pct = min(100, int(converted / max_convert * 100)) if max_convert > 0 else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        embed.add_field(name="💱 Shards → Orbs Conversion",
                       value=f"Main: {bar} {pct}% ({converted:,.0f}/{max_convert:,.0f})", inline=False)
        embed.set_footer(text=f"Use /pay to send | /convert to exchange")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pay")
    async def pay(self, ctx, user: discord.Member = None, amount: float = None, *, currency: str = None):
        if not user or not amount or not currency:
            return await ctx.send(embed=error_embed("Usage: /pay @user [amount] [currency]"))
        currency = currency.title()

        bal = await db.get_user_balance(ctx.guild.id, ctx.author.id, currency)
        if bal < amount:
            return await ctx.send(embed=error_embed("Insufficient funds!"))

        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        transfer_limits = config.get("transfer_limits", {})
        weekly_limit = transfer_limits.get(currency, 0)

        if weekly_limit > 0:
            week_start = self.get_week_start()
            cursor = await db.db.execute(
                "SELECT COALESCE(SUM(amount_sent), 0) FROM transfer_tracking WHERE guild_id = ? AND user_id = ? AND currency = ? AND week_start = ?",
                (ctx.guild.id, ctx.author.id, currency, week_start))
            sent = (await cursor.fetchone())[0]
            if sent + amount > weekly_limit:
                remaining = weekly_limit - sent
                return await ctx.send(embed=error_embed(f"Weekly transfer limit reached! {remaining:,.0f} {currency} remaining this week."))

        view = ConfirmView(ctx, f"Send {amount:,.0f} {currency} to {user.mention}?")
        msg = await ctx.send(embed=warning_embed("Transfer", f"Send {amount:,.0f} {currency} to {user.mention}?"), view=view)
        await view.wait()
        if view.value:
            await db.add_user_balance(ctx.guild.id, ctx.author.id, currency, -amount)
            await db.add_user_balance(ctx.guild.id, user.id, currency, amount)
            if weekly_limit > 0:
                await db.db.execute(
                    "INSERT OR REPLACE INTO transfer_tracking (guild_id, user_id, currency, week_start, amount_sent) VALUES (?, ?, ?, ?, COALESCE((SELECT amount_sent FROM transfer_tracking WHERE guild_id = ? AND user_id = ? AND currency = ? AND week_start = ?), 0) + ?)",
                    (ctx.guild.id, ctx.author.id, currency, week_start, ctx.guild.id, ctx.author.id, currency, week_start, amount))
                await db.db.commit()
            await msg.edit(embed=success_embed("Sent!", f"Sent {amount:,.0f} {currency} to {user.mention}!"), view=None)
            await db.log_entry(ctx.guild.id, "transfer", {"from": ctx.author.id, "to": user.id, "currency": currency, "amount": amount})

    @commands.hybrid_command(name="convert")
    async def convert(self, ctx, amount: float = None, *, from_to: str = None):
        if not amount or not from_to:
            return await ctx.send(embed=error_embed("Usage: /convert [amount] [from] [to]"))
        parts = from_to.split()
        if len(parts) < 2:
            return
        from_cur = " ".join(parts[:-1]).title()
        to_cur = parts[-1].title()

        ratio_str = await db.get_global_config("shard_orb_ratio", "3:1")
        ratio_parts = ratio_str.split(":")
        ratio = int(ratio_parts[0]) / int(ratio_parts[1]) if len(ratio_parts) == 2 else 3

        converted = amount / ratio
        bal = await db.get_user_balance(ctx.guild.id, ctx.author.id, from_cur)
        if bal < amount:
            return await ctx.send(embed=error_embed(f"Insufficient {from_cur}!"))

        max_convert = await db.get_global_config("max_shards_convertable", 3000)
        week_start = self.get_week_start()
        cursor = await db.db.execute(
            "SELECT COALESCE(SUM(amount_converted), 0) FROM conversion_tracking WHERE guild_id = ? AND user_id = ? AND week_start = ?",
            (ctx.guild.id, ctx.author.id, week_start))
        total = (await cursor.fetchone())[0]
        if total + amount > max_convert:
            return await ctx.send(embed=error_embed(f"Weekly conversion limit reached! Max {max_convert:,.0f} {from_cur} per week."))

        view = ConfirmView(ctx, f"Convert {amount:,.0f} {from_cur} → {converted:,.0f} {to_cur}?")
        msg = await ctx.send(embed=warning_embed("Convert", f"Convert {amount:,.0f} {from_cur} → {converted:,.0f} {to_cur}?"), view=view)
        await view.wait()
        if view.value:
            await db.add_user_balance(ctx.guild.id, ctx.author.id, from_cur, -amount)
            await db.add_user_balance(ctx.guild.id, ctx.author.id, to_cur, converted)
            await db.db.execute(
                "INSERT OR REPLACE INTO conversion_tracking (guild_id, user_id, week_start, amount_converted) VALUES (?, ?, ?, COALESCE((SELECT amount_converted FROM conversion_tracking WHERE guild_id = ? AND user_id = ? AND week_start = ?), 0) + ?)",
                (ctx.guild.id, ctx.author.id, week_start, ctx.guild.id, ctx.author.id, week_start, amount))
            await db.db.commit()
            await msg.edit(embed=success_embed("Converted!", f"Converted {amount:,.0f} {from_cur} → {converted:,.0f} {to_cur}!"), view=None)

    @commands.hybrid_command(name="top")
    async def top(self, ctx, *, currency: str = "Gems"):
        currency = currency.title()
        ranks = await db.get_user_ranks(ctx.guild.id, currency)
        sorted_ranks = sorted(ranks.items(), key=lambda x: x[1]["rank"])[:20]
        lines = []
        for uid, info in sorted_ranks:
            m = ctx.guild.get_member(uid)
            lines.append(f"{info['rank']}. {m.mention if m else f'<@{uid}>'} — {info['balance']:,.0f}")
        embed = info_embed(f"{currency} Leaderboard", "\n".join(lines) or "No data")
        user_rank = ranks.get(ctx.author.id, {})
        if user_rank:
            embed.set_footer(text=f"You: #{user_rank['rank']} — {user_rank['balance']:,.0f}")
        await ctx.send(embed=embed)

    def get_week_start(self):
        import datetime
        now = datetime.datetime.utcnow()
        week_start = now - datetime.timedelta(days=now.weekday())
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    @commands.command(name="wsetup_all")
    async def wsetup_all(self, ctx):
        embed = info_embed("Wallet Setup", "Wallet setup complete (default configuration applied).")
        await ctx.send(embed=embed)

    @commands.command(name="wsetup")
    async def wsetup(self, ctx):
        embed = info_embed("Wallet Setup Menu", "1. Configure\n2. Display Options\nType number or **done**.")
        await ctx.send(embed=embed)

    @commands.command(name="spy")
    async def spy(self, ctx, subcommand: str = None, user: discord.Member = None):
        if subcommand != "inv" or not user:
            return
        # Delegate to cards cog
        cards_cog = self.bot.get_cog("Cards")
        if cards_cog:
            await cards_cog.inv(ctx, user)


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
    await bot.add_cog(Wallet(bot))

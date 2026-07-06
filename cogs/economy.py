import discord
from discord.ext import commands
import time
import json
import random
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *
from cogs.owner import ConfirmView


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="esetup_all")
    @has_spower()
    async def esetup_all(self, ctx):
        embed = info_embed("Economy Setup Wizard", "Let's set up the economy!")
        view = ConfirmView(ctx, "Start?")
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if not view.value:
            return
        config = {"currencies": {}, "initial_capital": {}, "earning": {},
                  "blacklist_roles": {}, "boosts": {}, "transfer_limits": {},
                  "conversion": {}}
        try:
            await msg.edit(embed=info_embed("Step 1: Currency Setup", "Enable Gems?\nReply **-y** or **skip**."), view=None)
            r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            if r.lower() == "-y":
                config["currencies"]["Gems"] = "💎"

            await ctx.send(embed=info_embed("Enable Crystal Shards?"))
            r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            if r.lower() == "-y":
                config["currencies"]["Crystal Shards"] = "💠"

            await ctx.send(embed=info_embed("Enable Vanishing Orbs?"))
            r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            if r.lower() == "-y":
                config["currencies"]["Vanishing Orbs"] = "👁️"

            await ctx.send(embed=info_embed("Custom currency name? (or **skip**)"))
            r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            if r.lower() != "skip":
                name = r
                await ctx.send("Emoji?")
                emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                config["currencies"][name] = emoji
                config["initial_capital"][name] = 0

            await ctx.send(embed=info_embed("Step 2: Initial Capital", "Initial capital for Gems? (0 for none)"))
            for cur in config["currencies"]:
                if cur not in config["initial_capital"]:
                    r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                    try:
                        config["initial_capital"][cur] = float(r)
                    except:
                        config["initial_capital"][cur] = 0
                    if list(config["currencies"].keys())[-1] != cur:
                        await ctx.send(f"Initial capital for {cur}?")

            await db.set_guild_config(ctx.guild.id, "economy_config", config)
            await ctx.send(embed=success_embed("Economy setup complete!"))

            # Ensure existing users get initial balances
            for member in ctx.guild.members:
                if not member.bot:
                    await db.ensure_user(ctx.guild.id, member.id)
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="esetup")
    @has_spower()
    async def esetup(self, ctx):
        embed = info_embed("Economy Setup Menu",
            "1. Currency Setup\n2. Initial Capital\n3. Earning Setup\n"
            "4. Blacklist Roles\n5. Boosts\n6. Transfer & Conversion Limits\n\n"
            "Type number or **done**.")
        await ctx.send(embed=embed)

    @commands.command(name="spawn")
    @has_spower()
    async def spawn(self, ctx, currency: str = None, amount: float = None):
        if not currency or not amount:
            return await ctx.send(embed=error_embed("Usage: /spawn [currency] [amount]"))
        await ctx.send(embed=warning_embed("Spawn Currency",
            f"Spawn {amount:,.0f} {currency} in this channel?\n"
            "Users can claim by reacting."))
        msg = await ctx.send("React to claim!")
        await msg.add_reaction("💰")
        # Simple reaction-based spawn
        def check(reaction, user):
            return reaction.message.id == msg.id and str(reaction.emoji) == "💰" and not user.bot
        claimed = set()
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30, check=check)
                if user.id not in claimed:
                    await db.add_user_balance(ctx.guild.id, user.id, currency, amount)
                    claimed.add(user.id)
                    await ctx.send(f"{user.mention} claimed {amount:,.0f} {currency}!")
            except:
                break
        await msg.edit(content="Spawning finished!")

    @commands.command(name="destroy")
    @has_spower()
    async def destroy(self, ctx, currency: str = None, amount: float = None):
        if not currency or not amount:
            return await ctx.send(embed=error_embed("Usage: /destroy [currency] [amount]"))
        view = ConfirmView(ctx, f"Destroy {amount:,.0f} {currency} from everyone?")
        msg = await ctx.send(embed=warning_embed("Destroy Currency", f"This will remove {amount:,.0f} {currency} from ALL users."), view=view)
        await view.wait()
        if view.value:
            for member in ctx.guild.members:
                if not member.bot:
                    bal = await db.get_user_balance(ctx.guild.id, member.id, currency)
                    new_bal = max(0, bal - amount)
                    await db.set_user_balance(ctx.guild.id, member.id, currency, new_bal)
            await msg.edit(embed=success_embed("Destroyed", f"Destroyed {amount:,.0f} {currency} from everyone."), view=None)


async def setup(bot):
    await bot.add_cog(Economy(bot))

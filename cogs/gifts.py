import discord
from discord.ext import commands
import json
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *
from cogs.owner import CurrencySelectView


class Gifts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gsetup_all")
    @has_spower()
    async def gsetup_all(self, ctx):
        embed = info_embed("Gift Setup Wizard", "Select currency:")
        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        currencies = config.get("currencies", {"Gems": "💎"})
        view = CurrencySelectView(list(currencies.keys()), list(currencies.values()))
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.selected is None:
            return
        currency = view.selected
        items = await db.get_shop_items(ctx.guild.id, currency)
        lines = [f"{i+1}. {item['emoji'] or ''} {item['item_name']}" for i, item in enumerate(items)]
        embed2 = info_embed(f"Which item can be gifted for {currency}?", "\n".join(lines))
        await msg.edit(embed=embed2, view=None)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            idx = int(reply.content.strip()) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                await ctx.send(f"Chance % for {item['item_name']} as gift? (1-100)")
                chance = float((await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip())
                await db.db.execute(
                    "INSERT OR REPLACE INTO gift_config (guild_id, currency, item_name, chance) VALUES (?, ?, ?, ?)",
                    (ctx.guild.id, currency, item['item_name'], chance))
                await db.db.commit()
                await ctx.send(embed=success_embed(f"{chance}% chance for {item['item_name']} when buying with {currency}."))
        except:
            pass

    @commands.command(name="gsetup")
    @has_spower()
    async def gsetup(self, ctx):
        embed = info_embed("Gift Setup Menu", "Select currency:")
        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        currencies = config.get("currencies", {"Gems": "💎"})
        view = CurrencySelectView(list(currencies.keys()), list(currencies.values()))
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.selected:
            cursor = await db.db.execute(
                "SELECT item_name, chance FROM gift_config WHERE guild_id = ? AND currency = ?",
                (ctx.guild.id, view.selected))
            rows = await cursor.fetchall()
            lines = [f"{i+1}. {name} — {chance}%" for i, (name, chance) in enumerate(rows)] if rows else ["No items configured"]
            await msg.edit(embed=info_embed(f"{view.selected} Gift Chances", "\n".join(lines)), view=None)


async def setup(bot):
    await bot.add_cog(Gifts(bot))

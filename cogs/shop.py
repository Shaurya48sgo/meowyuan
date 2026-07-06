import discord
from discord.ext import commands
import json
import random
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *
from cogs.owner import ConfirmView, CurrencySelectView


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="shop")
    async def shop(self, ctx):
        embed = info_embed("Shop", "Select a currency:", private=True)
        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        currencies = config.get("currencies", {"Gems": "💎", "Crystal Shards": "💠", "Vanishing Orbs": "👁️", "Dragon Coins": "🐉"})
        view = CurrencySelectView(list(currencies.keys()), list(currencies.values()))
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.selected is None:
            return

        currency = view.selected
        items = await db.get_shop_items(ctx.guild.id, currency)
        if not items:
            return await msg.edit(embed=info_embed(f"{currency} Shop", "No items available.", private=True), view=None)

        user_bal = await db.get_user_balance(ctx.guild.id, ctx.author.id, currency)
        lines = []
        for i, item in enumerate(items):
            stock_text = "∞" if item["stock"] == -1 else f"Stock: {item['stock']}" if item["stock"] > 0 else "Out of Stock"
            lines.append(f"{i+1}. {item['emoji'] or ''} **{item['item_name']}** — {item['price']:,.0f} {currency}")
            if item.get("description"):
                lines.append(f"   {item['description']}")
            lines.append(f"   {stock_text}")

        embed2 = info_embed(f"{currency} Shop", "\n".join(lines), private=True)
        embed2.set_footer(text=f"Your balance: {user_bal:,.0f} {currency}")
        await msg.edit(embed=embed2, view=None)

        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            idx = int(reply.content.strip()) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                if item["stock"] == 0:
                    return await ctx.send(embed=error_embed("Out of stock!"), ephemeral=True)
                if user_bal < item["price"]:
                    return await ctx.send(embed=error_embed("Insufficient funds!"), ephemeral=True)

                view2 = ConfirmView(ctx, f"Buy {item['item_name']} for {item['price']:,.0f} {currency}?")
                msg2 = await ctx.send(embed=warning_embed("Purchase", f"Buy {item['item_name']} for {item['price']:,.0f} {currency}?"), view=view2)
                await view2.wait()
                if view2.value:
                    await db.add_user_balance(ctx.guild.id, ctx.author.id, currency, -item["price"])
                    await db.add_inventory(ctx.guild.id, ctx.author.id, item["item_name"])
                    if item["stock"] > 0:
                        await db.db.execute(
                            "UPDATE shop_items SET stock = stock - 1 WHERE guild_id = ? AND currency = ? AND item_name = ?",
                            (ctx.guild.id, currency, item["item_name"]))
                        await db.db.commit()

                    # Check for bonus gift
                    await self.check_bonus_gift(ctx, currency)

                    await msg2.edit(embed=success_embed("Purchased!",
                        f"Bought {item['item_name']} for {item['price']:,.0f} {currency}."), view=None)
                    await db.log_entry(ctx.guild.id, "purchase", {"user": ctx.author.id, "item": item["item_name"],
                                                                  "currency": currency, "price": item["price"]})
        except ValueError:
            pass
        except:
            pass

    async def check_bonus_gift(self, ctx, currency):
        cursor = await db.db.execute(
            "SELECT item_name, chance FROM gift_config WHERE guild_id = ? AND currency = ?",
            (ctx.guild.id, currency))
        for row in await cursor.fetchall():
            if random.random() * 100 < row[1]:
                await db.add_inventory(ctx.guild.id, ctx.author.id, row[0])
                await ctx.send(embed=success_embed("Bonus Gift!", f"🎁 You received a bonus **{row[0]}**!"))

    @commands.command(name="shopitems_all")
    @has_spower()
    async def shopitems_all(self, ctx):
        embed = info_embed("Item Setup Wizard", "Setting up items for sale.")
        await ctx.send(embed=embed)
        await self._add_items_wizard(ctx, "Gems")

    async def _add_items_wizard(self, ctx, currency):
        default_items = [
            ("Silence 2min", 100, 100, "🔒", "Jail someone for 2 minutes"),
            ("Silence 5min", 200, 100, "🔒", "Jail someone for 5 minutes"),
            ("Silence Pro 2min", 300, 50, "🔒", "PRO jail for 2 minutes"),
            ("Silence Pro 5min", 500, 50, "🔒", "PRO jail for 5 minutes"),
            ("Immunity", 500, 50, "🛡️", "Block non-PRO jails for 16h"),
            ("Full Immunity", 800, 30, "🛡️", "Block ALL jails for 16h"),
            ("Reverse", 400, 50, "🔄", "Reverse non-PRO jails for 8h"),
            ("Divine Eye", 300, 100, "👁️", "See all active protections"),
            ("Invis Pot", 350, 75, "🫥", "Hide from logs for 6h"),
            ("Mysterious Thief", 450, 40, "🦹", "Steal normal jails for 3h"),
        ]
        for name, price, stock, emoji, desc in default_items:
            await db.db.execute(
                "INSERT OR REPLACE INTO shop_items (guild_id, currency, item_name, price, stock, description, emoji, default_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ctx.guild.id, currency, name, price, stock, desc, emoji, stock))
        await db.db.commit()
        await ctx.send(embed=success_embed(f"{currency} shop items added!"))

    @commands.command(name="shopitems")
    @has_spower()
    async def shopitems(self, ctx):
        embed = info_embed("Shop Setup", "Select currency:")
        config = await db.get_guild_config(ctx.guild.id, "economy_config", {})
        currencies = config.get("currencies", {"Gems": "💎"})
        view = CurrencySelectView(list(currencies.keys()), list(currencies.values()))
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.selected is None:
            return
        items = await db.get_shop_items(ctx.guild.id, view.selected)
        lines = [f"{i+1}. {item['emoji'] or ''} {item['item_name']} — {item['price']} | Stock: {item.get('stock', '∞')}" for i, item in enumerate(items)]
        embed2 = info_embed(f"{view.selected} Shop Items", "\n".join(lines) or "No items")
        await msg.edit(embed=embed2, view=None)

    @commands.hybrid_command(name="setitemstock")
    @has_spower()
    async def set_itemstock(self, ctx, currency: str = None, *, item_and_stock: str = None):
        if not currency or not item_and_stock:
            return await ctx.send(embed=error_embed("Usage: /set itemstock [currency] [item] [quantity]"))
        parts = item_and_stock.rsplit(" ", 1)
        if len(parts) != 2:
            return
        item_name, qty = parts[0], int(parts[1])
        view = ConfirmView(ctx, f"Set {item_name} stock to {qty}?")
        msg = await ctx.send(embed=warning_embed("Set Stock", f"Set {item_name} stock to {qty}?"), view=view)
        await view.wait()
        if view.value:
            await db.db.execute(
                "UPDATE shop_items SET stock = ? WHERE guild_id = ? AND currency = ? AND item_name = ?",
                (qty, ctx.guild.id, currency, item_name))
            await db.db.commit()
            await msg.edit(embed=success_embed("Stock Set", f"{item_name} stock set to {qty}!"), view=None)

    @commands.hybrid_command(name="refreshstock")
    @has_spower()
    async def refresh_stock(self, ctx):
        view = ConfirmView(ctx, "Refresh ALL stock to default values?")
        msg = await ctx.send(embed=warning_embed("Refresh Stock", "Refresh ALL stock to default values?"), view=view)
        await view.wait()
        if view.value:
            await db.db.execute(
                "UPDATE shop_items SET stock = default_stock WHERE guild_id = ?", (ctx.guild.id,))
            await db.db.commit()
            await msg.edit(embed=success_embed("Stock Refreshed", "All stock refreshed to default values!"), view=None)

    @commands.hybrid_command(name="itemrefreshstock")
    @has_spower()
    async def item_refresh_stock(self, ctx, currency: str = None, *, item_name: str = None):
        if not currency or not item_name:
            return
        view = ConfirmView(ctx, f"Refresh {item_name} stock?")
        msg = await ctx.send(embed=warning_embed("Refresh Stock", f"Refresh {item_name} stock?"), view=view)
        await view.wait()
        if view.value:
            await db.db.execute(
                "UPDATE shop_items SET stock = default_stock WHERE guild_id = ? AND currency = ? AND item_name = ?",
                (ctx.guild.id, currency, item_name))
            await db.db.commit()
            await msg.edit(embed=success_embed("Refreshed", f"{item_name} stock refreshed!"), view=None)

    @commands.hybrid_command(name="defaultstock")
    @has_spower()
    async def defaultstock(self, ctx):
        embed = info_embed("Default Stock Settings")
        for currency in ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]:
            items = await db.get_shop_items(ctx.guild.id, currency)
            if items:
                lines = [f"{i+1}. {item['emoji'] or ''} {item['item_name']} — Default: {item.get('default_stock', '∞')}" for i, item in enumerate(items[:5])]
                embed.add_field(name=currency, value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Shop(bot))

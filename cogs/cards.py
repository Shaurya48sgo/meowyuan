import discord
from discord.ext import commands
import time
import json
from utils.database import db
from utils.embeds import *


ITEMS_INFO = {
    "Immunity": {"duration": 57600, "slot_type": "normal", "desc": "Blocks non-PRO jails. PRO jails jail you instead."},
    "Full Immunity": {"duration": 57600, "slot_type": "pro", "desc": "Blocks ALL jails. They will be wasted."},
    "Reverse": {"duration": 28800, "slot_type": "normal", "desc": "Non-PRO jails bounce back. PRO jails jail you."},
    "Divine Eye": {"duration": 21600, "slot_type": None, "desc": "See active protections."},
    "Invis Pot": {"duration": 21600, "slot_type": None, "desc": "Hide from logs for 6 hours."},
    "Mysterious Thief": {"duration": 10800, "slot_type": "normal", "desc": "Steal normal jail attempts for 3 hours. Only works when no other card is active in that slot."},
    "Silence 2min": {"duration": 120, "slot_type": "power", "desc": "Jail someone for 2 minutes."},
    "Silence 5min": {"duration": 300, "slot_type": "power", "desc": "Jail someone for 5 minutes."},
    "Silence Pro 2min": {"duration": 120, "slot_type": "power", "desc": "PRO jail someone for 2 minutes."},
    "Silence Pro 5min": {"duration": 300, "slot_type": "power", "desc": "PRO jail someone for 5 minutes."},
}


class Cards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="inv")
    async def inv(self, ctx, user: discord.Member = None):
        target = user or ctx.author
        is_own = target == ctx.author
        can_spy = False
        if not is_own:
            if await db.has_power(ctx.guild.id, ctx.author.id) or await db.is_global_dev(ctx.author.id) or ctx.author.id == self.bot.owner_id:
                can_spy = True
            if not can_spy:
                return await ctx.send(embed=error_embed("You cannot view others' inventories."), ephemeral=True)

        inventory = await db.get_inventory(ctx.guild.id, target.id)
        embed = info_embed(f"{'Spy View: ' if not is_own else ''}{target.display_name}'s Inventory", private=is_own or can_spy)

        normal_slots = []
        cursor = await db.db.execute(
            "SELECT slot_num, item_name, expires_at FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = 'normal' ORDER BY slot_num",
            (ctx.guild.id, target.id))
        slots = {r[1]: (r[0], r[2]) for r in await cursor.fetchall()}
        for i in range(1, 6):
            found = None
            for name, (num, exp) in slots.items():
                if num == i and exp > time.time():
                    found = name
                    break
            normal_slots.append(f"{i}. {found or 'Empty'}")

        pro_slots = []
        cursor = await db.db.execute(
            "SELECT slot_num, item_name, expires_at FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = 'pro' ORDER BY slot_num",
            (ctx.guild.id, target.id))
        slots = {(r[1], r[0], r[2]) for r in await cursor.fetchall()}
        pro_items = {(r[0], r[1], r[2]) for r in await cursor.fetchall() if r[2] > time.time()}
        for i in range(1, 4):
            found = None
            for name, num, exp in pro_items:
                if num == i:
                    found = name
                    break
            pro_slots.append(f"{i}. {found or 'Empty'}")

        embed.add_field(name="Normal Jail Cards (5 slots):", value="\n".join(normal_slots), inline=False)
        embed.add_field(name="PRO Jail Cards (3 slots):", value="\n".join(pro_slots), inline=False)

        stock_lines = [f"• {name} x {qty}" for name, qty in inventory.items() if qty > 0]
        if stock_lines:
            embed.add_field(name="Stock:", value="\n".join(stock_lines[:10]), inline=False)

        cursor = await db.db.execute(
            "SELECT item_name, quantity FROM unclaimed_gifts WHERE guild_id = ? AND user_id = ? AND expires_at > ?",
            (ctx.guild.id, target.id, time.time()))
        gifts = {r[0]: r[1] for r in await cursor.fetchall()}
        if gifts:
            embed.add_field(name="Unclaimed Gifts:",
                          value="\n".join(f"• {qty}x {name}" for name, qty in gifts.items()), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="use")
    async def use(self, ctx, *, item_name: str = None):
        if item_name:
            await self.use_item(ctx, item_name)
            return
        embed = info_embed("Use Items", "What would you like to use?\n\n"
            "1. Immunity\n2. Full Immunity\n3. Reverse\n4. Divine Eye\n"
            "5. Invis Pot\n6. Mysterious Thief\n7. Jail Powers\n8. Custom Roles\n"
            "9. Temp Roles\n\nType number or **back**.", private=True)
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            choice = reply.content.strip()
            map_items = {"1": "Immunity", "2": "Full Immunity", "3": "Reverse", "4": "Divine Eye",
                        "5": "Invis Pot", "6": "Mysterious Thief"}
            if choice in map_items:
                await self.use_item(ctx, map_items[choice])
            elif choice == "7":
                await self.use_jail_power(ctx)
        except:
            pass

    async def use_item(self, ctx, item_name: str):
        inventory = await db.get_inventory(ctx.guild.id, ctx.author.id)
        if inventory.get(item_name, 0) < 1:
            return await ctx.send(embed=error_embed(f"You don't have {item_name}!"))

        info = ITEMS_INFO.get(item_name)
        if not info:
            return await ctx.send(embed=error_embed("Unknown item."))

        if info["slot_type"] in ("normal", "pro"):
            slot_type = info["slot_type"]
            max_slots = 5 if slot_type == "normal" else 3
            cursor = await db.db.execute(
                "SELECT slot_num FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = ? AND expires_at > ?",
                (ctx.guild.id, ctx.author.id, slot_type, time.time()))
            used = {r[0] for r in await cursor.fetchall()}
            available = [i for i in range(1, max_slots + 1) if i not in used]
            if not available:
                return await ctx.send(embed=error_embed(f"No free {slot_type} slots!"))

            slot = available[0]
            expires = time.time() + info["duration"]
            await db.add_inventory(ctx.guild.id, ctx.author.id, item_name, -1)
            await db.db.execute(
                "INSERT OR REPLACE INTO card_slots (guild_id, user_id, slot_type, slot_num, item_name, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (ctx.guild.id, ctx.author.id, slot_type, slot, item_name, expires))
            await db.db.commit()
            hours = info["duration"] / 3600
            await ctx.send(embed=success_embed(f"{item_name} Activated",
                f"You activated **{item_name}**! Lasts {hours:.0f} hours.\n{info['desc']}\nPlaced in {slot_type} slot {slot}."))
        elif item_name == "Divine Eye":
            await self.divine_eye(ctx)
        elif item_name == "Invis Pot":
            expires = time.time() + info["duration"]
            await db.add_inventory(ctx.guild.id, ctx.author.id, item_name, -1)
            await db.db.execute(
                "INSERT OR REPLACE INTO card_slots (guild_id, user_id, slot_type, slot_num, item_name, expires_at) VALUES (?, ?, 'buff', 1, ?, ?)",
                (ctx.guild.id, ctx.author.id, item_name, expires))
            await db.db.commit()
            await ctx.send(embed=success_embed("Invis Pot Activated",
                "You activated **Invis Pot**! You are hidden for 6 hours.\nYour name will appear as **Mysterious Person** in logs."))

    async def divine_eye(self, ctx):
        lines = []
        cursor = await db.db.execute(
            "SELECT user_id, item_name FROM card_slots WHERE guild_id = ? AND slot_type IN ('normal', 'pro') AND expires_at > ?",
            (ctx.guild.id, time.time()))
        active = {}
        for row in await cursor.fetchall():
            uid, name = row
            if uid not in active:
                active[uid] = []
            active[uid].append(name)
        for uid, items in active.items():
            m = ctx.guild.get_member(uid)
            if m:
                # Check if they have Invis Pot active
                cursor2 = await db.db.execute(
                    "SELECT 1 FROM card_slots WHERE guild_id = ? AND user_id = ? AND item_name = 'Invis Pot' AND expires_at > ?",
                    (ctx.guild.id, uid, time.time()))
                if await cursor2.fetchone():
                    continue
                lines.append(f"• {m.mention} — {', '.join(items)}")
        embed = info_embed("Divine Eye Activated", "\n".join(lines) or "No active protections.", private=True)
        await ctx.send(embed=embed)
        await db.add_inventory(ctx.guild.id, ctx.author.id, "Divine Eye", -1)

    async def use_jail_power(self, ctx):
        embed = info_embed("Jail Powers",
            "1. Silence 2min\n2. Silence 5min\n3. Silence Pro 2min\n4. Silence Pro 5min\n\nType number.", private=True)
        await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            items = {"1": "Silence 2min", "2": "Silence 5min", "3": "Silence Pro 2min", "4": "Silence Pro 5min"}
            item = items.get(reply.content.strip())
            if not item:
                return
            inventory = await db.get_inventory(ctx.guild.id, ctx.author.id)
            if inventory.get(item, 0) < 1:
                return await ctx.send(embed=error_embed(f"You don't have {item}!"))
            await ctx.send("Who to jail? @mention")
            target = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            if target.content.startswith("<@"):
                uid = int(target.content.strip("<@!>"))
                member = ctx.guild.get_member(uid)
                if member:
                    power = item.replace("Silence ", "").replace(" 2min", "2min").replace(" 5min", "5min")
                    if "Pro" in item:
                        power = power.replace("Pro ", "") + " PRO"
                    await db.remove_inventory(ctx.guild.id, ctx.author.id, item)
                    jail_cog = self.bot.get_cog("Jail")
                    if jail_cog:
                        ctx.author = member  # Actually we need to jail target, not use author
                        await jail_cog.jail(ctx, member, power)
                    else:
                        await ctx.send(embed=success_embed(f"You jailed {member.mention}!"))
        except:
            pass

    @commands.command(name="managecards")
    async def managecards(self, ctx):
        embed = info_embed("Manage Cards",
            "Type **normal [slot] [item]** or **pro [slot] [item]** to place.\n"
            "Type **remove normal [slot]** or **remove pro [slot]** to remove.\n"
            "Type **back** to go back.", private=True)
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            parts = reply.content.strip().split()
            if len(parts) >= 2 and parts[0].lower() == "remove":
                slot_type = parts[1].lower()
                slot_num = int(parts[2]) if len(parts) > 2 else 1
                await db.db.execute(
                    "DELETE FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = ? AND slot_num = ?",
                    (ctx.guild.id, ctx.author.id, slot_type, slot_num))
                await db.db.commit()
                await ctx.send(embed=success_embed(f"Cleared {slot_type} slot {slot_num}."))
        except:
            pass

    @commands.command(name="claimgifts")
    async def claimgifts(self, ctx):
        cursor = await db.db.execute(
            "SELECT id, item_name, quantity FROM unclaimed_gifts WHERE guild_id = ? AND user_id = ? AND expires_at > ?",
            (ctx.guild.id, ctx.author.id, time.time()))
        gifts = await cursor.fetchall()
        if not gifts:
            return await ctx.send(embed=info_embed("No Gifts", "No unclaimed gifts.", private=True))
        for gid, name, qty in gifts:
            await db.add_inventory(ctx.guild.id, ctx.author.id, name, qty)
            await db.db.execute("DELETE FROM unclaimed_gifts WHERE id = ?", (gid,))
        await db.db.commit()
        await ctx.send(embed=success_embed("Gifts Claimed", "All gifts have been claimed and added to your inventory."))


async def setup(bot):
    await bot.add_cog(Cards(bot))

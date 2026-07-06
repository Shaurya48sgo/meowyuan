import discord
from discord.ext import commands
from utils.database import db
from utils.checks import is_owner_or_dev, has_spower, has_power, has_any_power
from utils.embeds import *


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dev")
    @is_owner_or_dev()
    async def dev(self, ctx, action: str = None, member: discord.Member = None):
        if not action or member is None:
            return await ctx.send(embed=error_embed("Usage: I?dev add/remove @mention"))
        if action.lower() == "add":
            view = ConfirmView(ctx, f"Add {member.mention} as Global Developer?")
            msg = await ctx.send(embed=warning_embed("Add Developer", f"Add {member.mention} as **Global Developer**?"), view=view)
            await view.wait()
            if view.value:
                await db.add_global_dev(member.id)
                await msg.edit(embed=success_embed("Added", f"{member.mention} added as **Global Developer**."), view=None)
                await db.log_entry(ctx.guild.id, "dev_add", {"user": member.id, "by": ctx.author.id})
        elif action.lower() == "remove":
            view = ConfirmView(ctx, f"Remove {member.mention} from Global Developers?")
            msg = await ctx.send(embed=warning_embed("Remove Developer", f"Remove {member.mention} from Global Developers?"), view=view)
            await view.wait()
            if view.value:
                await db.remove_global_dev(member.id)
                await msg.edit(embed=success_embed("Removed", f"{member.mention} removed from Global Developers."), view=None)

    @commands.command(name="devlist")
    @is_owner_or_dev()
    async def devlist(self, ctx):
        devs = await db.list_global_devs()
        lines = []
        for uid in devs:
            u = self.bot.get_user(uid)
            lines.append(f"{u.mention if u else f'<@{uid}>'}")
        embed = info_embed("Global Developers", "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)))
        embed.set_footer(text=f"Total: {len(devs)} developers")
        await ctx.send(embed=embed)

    @commands.command(name="infinity")
    @is_owner_or_dev()
    async def infinity(self, ctx, member: discord.Member = None, flag: str = None):
        if not member or flag not in ("-y", "-r"):
            return await ctx.send(embed=error_embed("Usage: I?infinity @mention -y/-r"))
        if flag == "-y":
            view = ConfirmView(ctx, f"Make {member.mention} an **Infinity** user?")
            msg = await ctx.send(embed=warning_embed("Infinity",
                f"Make {member.mention} an **Infinity**?\n"
                "They will have infinite EVERYTHING in ALL servers: all currencies, all items, global currency.\n"
                "They can transfer without limits."), view=view)
            await view.wait()
            if view.value:
                await db.set_infinity(member.id, True)
                await msg.edit(embed=success_embed("Infinity", f"{member.mention} is now **Infinity**!"), view=None)
        else:
            view = ConfirmView(ctx, f"Remove {member.mention}'s Infinity status?")
            msg = await ctx.send(embed=warning_embed("Remove Infinity", f"Remove {member.mention}'s Infinity status?"), view=view)
            await view.wait()
            if view.value:
                await db.set_infinity(member.id, False)
                await msg.edit(embed=success_embed("Infinity Removed", f"{member.mention} is no longer Infinity."), view=None)

    @commands.command(name="hecker")
    @has_any_power()
    async def hecker(self, ctx, member: discord.Member = None, flag: str = None):
        if not member or flag not in ("-y", "-r"):
            return await ctx.send(embed=error_embed("Usage: I?hecker @mention -y/-r"))
        if flag == "-y":
            view = ConfirmView(ctx, f"Make {member.mention} a **Hecker**?")
            msg = await ctx.send(embed=warning_embed("Hecker",
                f"Make {member.mention} a **Hecker**?\n"
                "They will have infinite server currencies and items. NO global currency. NO setup power. NO transfers."), view=view)
            await view.wait()
            if view.value:
                await db.set_hecker(ctx.guild.id, member.id, True)
                await msg.edit(embed=success_embed("Hecker", f"{member.mention} is now **Hecker**!"), view=None)
        else:
            view = ConfirmView(ctx, f"Remove {member.mention}'s Hecker status?")
            msg = await ctx.send(embed=warning_embed("Remove Hecker", f"Remove {member.mention}'s Hecker status?"), view=view)
            await view.wait()
            if view.value:
                await db.set_hecker(ctx.guild.id, member.id, False)
                await msg.edit(embed=success_embed("Hecker Removed", f"{member.mention} is no longer Hecker."), view=None)

    @commands.command(name="spower")
    @is_owner_or_dev()
    async def spower(self, ctx, member: discord.Member = None, flag: str = None):
        if not member or flag not in ("-y", "-r"):
            return await ctx.send(embed=error_embed("Usage: I?spower @mention -y/-r"))
        if flag == "-y":
            view = ConfirmView(ctx, f"Give {member.mention} **Server Power**?")
            msg = await ctx.send(embed=warning_embed("Server Power",
                f"Give {member.mention} **Server Power**?\n"
                "They can use all setup commands, I?power, I?freeall, I?logs, I?hecker, I?accmerge, I?listaccmerge."), view=view)
            await view.wait()
            if view.value:
                await db.set_power(ctx.guild.id, member.id, "spower", True)
                await msg.edit(embed=success_embed("Server Power", f"{member.mention} now has **Server Power**!"), view=None)
        else:
            view = ConfirmView(ctx, f"Remove {member.mention}'s Server Power?")
            msg = await ctx.send(embed=warning_embed("Remove Server Power", f"Remove {member.mention}'s Server Power?"), view=view)
            await view.wait()
            if view.value:
                await db.set_power(ctx.guild.id, member.id, "spower", False)
                await msg.edit(embed=success_embed("Server Power Removed", f"{member.mention} no longer has Server Power."), view=None)

    @commands.command(name="power")
    @has_spower()
    async def power(self, ctx, target: str = None, flag: str = None):
        if not target or flag not in ("-y", "-r"):
            return await ctx.send(embed=error_embed("Usage: I?power @mention/@role -y/-r"))
        members = []
        is_role = False
        if target.startswith("<@&"):
            role_id = int(target.strip("<@&>"))
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send(embed=error_embed("Role not found"))
            members = role.members
            is_role = True
        elif target.startswith("<@"):
            uid = int(target.strip("<@!>"))
            m = ctx.guild.get_member(uid)
            if m:
                members = [m]
        if not members:
            return await ctx.send(embed=error_embed("No valid targets"))
        label = target if is_role else members[0].mention
        if flag == "-y":
            desc = f"Give all {label} members **Power**?" if is_role else f"Give {label} **Power**?"
            view = ConfirmView(ctx, desc)
            msg = await ctx.send(embed=warning_embed("Power", desc + "\nThey can use: I?freeall, I?logs, setup commands, I?give_coin, I?hecker, I?giftall, I?autogift."), view=view)
            await view.wait()
            if view.value:
                if is_role:
                    await db.db.execute("INSERT OR REPLACE INTO power_roles (guild_id, role_id) VALUES (?, ?)",
                                       (ctx.guild.id, role.id))
                    await db.db.commit()
                else:
                    await db.set_power(ctx.guild.id, members[0].id, "power", True)
                await msg.edit(embed=success_embed("Power", f"{label} {'all members' if is_role else ''} now has **Power**!"), view=None)
        else:
            desc = f"Remove {label}'s Power?" if not is_role else f"Remove Power from all {label} members?"
            view = ConfirmView(ctx, desc)
            msg = await ctx.send(embed=warning_embed("Remove Power", desc), view=view)
            await view.wait()
            if view.value:
                if is_role:
                    await db.db.execute("DELETE FROM power_roles WHERE guild_id = ? AND role_id = ?",
                                       (ctx.guild.id, role.id))
                    await db.db.commit()
                else:
                    await db.set_power(ctx.guild.id, members[0].id, "power", False)
                await msg.edit(embed=success_embed("Power Removed", f"{label} no longer has Power."), view=None)

    @commands.command(name="powerlist")
    @has_any_power()
    async def powerlist(self, ctx):
        spower_users = []
        power_users = []
        power_roles = []
        cursor = await db.db.execute("SELECT user_id, power_type FROM power_users WHERE guild_id = ?",
                                    (ctx.guild.id,))
        for row in await cursor.fetchall():
            uid, ptype = row
            m = ctx.guild.get_member(uid)
            mention = m.mention if m else f"<@{uid}>"
            if ptype == "spower":
                spower_users.append(mention)
            else:
                power_users.append(mention)
        cursor = await db.db.execute("SELECT role_id FROM power_roles WHERE guild_id = ?", (ctx.guild.id,))
        for row in await cursor.fetchall():
            r = ctx.guild.get_role(row[0])
            if r:
                power_roles.append(r.mention)
        embed = info_embed("Power Users", "", private=True)
        if spower_users:
            embed.add_field(name="Server Power (I?spower)",
                          value="\n".join(f"• {u}" for u in spower_users), inline=False)
        if power_users:
            embed.add_field(name="Power (I?power) — Users",
                          value="\n".join(f"• {u}" for u in power_users), inline=False)
        if power_roles:
            embed.add_field(name="Power (I?power) — Roles",
                          value="\n".join(f"• {r}" for r in power_roles), inline=False)
        if not spower_users and not power_users and not power_roles:
            embed.description = "No power users configured."
        await ctx.send(embed=embed)

    @commands.command(name="lockpower")
    @is_owner_or_dev()
    async def lockpower(self, ctx):
        locked = await db.get_global_config("power_lock", False)
        if locked:
            embed = warning_embed("Power Lock",
                "**Power Lock**\nCurrent: LOCKED\nReply **-y** to keep locked, **-n** to unlock.")
            msg = await ctx.send(embed=embed)
            try:
                reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                if reply.content.lower().strip() == "-n":
                    await db.set_global_config("power_lock", False)
                    await msg.edit(embed=success_embed("Power Unlocked", "Power unlocked! All Discord admins now have I?spower."), view=None)
            except:
                pass
        else:
            embed = warning_embed("Power Lock",
                "**Power Lock**\nCurrent: UNLOCKED (Discord admins have auto I?spower)\n"
                "Lock power so only you can grant I?spower?\nReply **-y** to lock, **-n** to unlock.")
            msg = await ctx.send(embed=embed)
            try:
                reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                if reply.content.lower().strip() == "-y":
                    await db.set_global_config("power_lock", True)
                    await msg.edit(embed=success_embed("Power Locked",
                        "Power locked! Only Owner, Devs, and I?spower holders can grant I?spower.\n"
                        "Discord admins NO LONGER have automatic I?spower."), view=None)
            except:
                pass

    @commands.command(name="server_reset")
    @has_spower()
    async def server_reset(self, ctx):
        view = ConfirmView(ctx, "PERMANENTLY delete ALL server data?")
        msg = await ctx.send(embed=warning_embed("SERVER RESET",
            "**WARNING: SERVER RESET**\nThis will PERMANENTLY delete:\n"
            "• All jail settings\n• All user data (balances, inventories, active items, cards)\n"
            "• All strike counts\n• All punishment history\n• All economy settings\n"
            "• All shop configurations\n• All icon role mappings\n• All reaction role messages\n"
            "• All gift settings\n• All wallet settings\n• All merged accounts\n• All logs history"), view=view)
        await view.wait()
        if view.value:
            await db.reset_guild(ctx.guild.id)
            await msg.edit(embed=success_embed("Server Reset", "Server has been reset. All data cleared."), view=None)

    @commands.command(name="freeall")
    @has_any_power()
    async def freeall(self, ctx):
        view = ConfirmView(ctx, "Free ALL jailed users?")
        msg = await ctx.send(embed=warning_embed("Free All", "Free ALL jailed users?"), view=view)
        await view.wait()
        if view.value:
            await db.db.execute("DELETE FROM jail_state WHERE guild_id = ?", (ctx.guild.id,))
            await db.db.commit()
            await msg.edit(embed=success_embed("Freed All", "**EVERYONE** is now free from **JAIL**!"), view=None)
            await db.log_entry(ctx.guild.id, "freeall", {"by": ctx.author.id})

    @commands.command(name="accmerge")
    @has_spower()
    async def accmerge(self, ctx, user1: discord.Member = None, user2: discord.Member = None, *, name: str = None):
        if not user1 or not user2:
            return await ctx.send(embed=error_embed("Usage: I?accmerge @user1 @user2 [name]"))
        name = name or "Merged Account"
        view = ConfirmView(ctx, f"Merge {user2.mention} into {user1.mention}?")
        msg = await ctx.send(embed=warning_embed("Account Merge",
            f"Merge {user2.mention} into {user1.mention}?\n"
            f"ALL data from {user2.mention} will be LOST and replaced with {user1.mention}'s data.\n"
            f"Merged name: \"{name}\""), view=view)
        await view.wait()
        if view.value:
            for currency in ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]:
                bal = await db.get_user_balance(ctx.guild.id, user1.id, currency)
                await db.set_user_balance(ctx.guild.id, user2.id, currency, bal)
            await db.db.execute(
                "INSERT OR REPLACE INTO merged_accounts (guild_id, primary_id, secondary_id, name) VALUES (?, ?, ?, ?)",
                (ctx.guild.id, user1.id, user2.id, name))
            await db.db.commit()
            await msg.edit(embed=success_embed("Accounts Merged",
                f"{user1.mention} and {user2.mention} are now synced as \"{name}\"."), view=None)

    @commands.command(name="listaccmerge")
    @has_spower()
    async def listaccmerge(self, ctx):
        cursor = await db.db.execute(
            "SELECT primary_id, secondary_id, name FROM merged_accounts WHERE guild_id = ?",
            (ctx.guild.id,))
        rows = await cursor.fetchall()
        if not rows:
            return await ctx.send(embed=info_embed("Merged Accounts", "No merged accounts."))
        groups = {}
        for p, s, n in rows:
            groups.setdefault(n, []).append((p, s))
        embed = info_embed("Merged Accounts")
        for name, pairs in groups.items():
            lines = []
            for p, s in pairs:
                pm = ctx.guild.get_member(p)
                sm = ctx.guild.get_member(s)
                lines.append(f"• {pm.mention if pm else f'<@{p}>'} (ID: {p})")
                lines.append(f"• {sm.mention if sm else f'<@{s}>'} (ID: {s})")
            embed.add_field(name=f"**\"{name}\"**", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="owner")
    @is_owner_or_dev()
    async def owner_cmd(self, ctx):
        embed = info_embed("Owner/Dev Commands",
            "• `I?dev add/remove @mention` — Manage global devs\n"
            "• `I?devlist` — List devs\n"
            "• `I?infinity @mention -y/-r` — Grant infinite everything\n"
            "• `I?spower @mention -y/-r` — Grant/remove Server Power\n"
            "• `I?lockpower` — Lock/unlock admin auto-I?spower\n"
            "• `I?gifsetup_all` — Configure jail GIFs (GLOBAL)\n"
            "• `I?gifsetup_reset` — Reset all GIFs\n"
            "• `I?gifsetup_list` — List GIFs\n"
            "• `I?gifplaysetup` — Configure play GIF commands\n"
            "• `I?djsetup` — Dev jail setup (GLOBAL)\n"
            "• `I?gcsetup` — Global currency setup\n"
            "• `I?theme` — Theme management\n"
            "• `I?devmenu` — Dev-only menu\n"
            "• `I?config` — View server config\n"
            "• `I?owner` — This menu")
        await ctx.send(embed=embed)

    @commands.command(name="devmenu")
    @is_owner_or_dev()
    async def devmenu(self, ctx):
        embed = info_embed("Dev Menu",
            "1. `I?gifsetup_all` — Jail GIFs (GLOBAL)\n"
            "2. `I?gifsetup_reset` — Reset GIFs\n"
            "3. `I?gifsetup_list` — List GIFs\n"
            "4. `I?gifplaysetup` — Play GIF commands\n"
            "5. `I?djsetup` — Dev Jail Setup (GLOBAL)\n"
            "6. `I?gcsetup` — Global Currency Setup\n"
            "7. `I?theme` — Theme Management\n"
            "8. `I?devconfig` — Dev Configuration\n"
            "Type number or **done**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            if reply.content.strip() == "8":
                await self.devconfig(ctx)
        except:
            pass

    async def devconfig(self, ctx):
        embed = info_embed("Dev Configuration",
            "1. Shards → Orbs Conversion Ratio\n"
            "   Current: 3:1\n\n"
            "2. Max Shards Convertable\n"
            "   Current: 3000\n\n"
            "Type number or **back**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            if reply.content.strip() == "1":
                await ctx.send("New ratio? (e.g., 3:1, 5:1)")
                reply2 = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                await db.set_global_config("shard_orb_ratio", reply2.content.strip())
                await ctx.send(embed=success_embed("Ratio updated", f"Ratio updated to {reply2.content.strip()}."))
            elif reply.content.strip() == "2":
                await ctx.send("New max Shards convertable per week?")
                reply2 = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                await db.set_global_config("max_shards_convertable", int(reply2.content.strip()))
                await ctx.send(embed=success_embed("Max updated", f"Max convertable updated to {reply2.content.strip()}."))
        except:
            pass

    @commands.command(name="give_coin")
    @has_any_power()
    async def give_coin(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send(embed=error_embed("Usage: I?give_coin @user"))
        currencies = ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]
        emojis = ["💎", "💠", "👁️", "🐉"]
        view = CurrencySelectView(currencies, emojis)
        msg = await ctx.send(embed=info_embed("Give/Remove Currency", "Select currency:"), view=view)
        await view.wait()
        if view.selected is None:
            return
        currency = view.selected
        await ctx.send(f"Amount? (use -{1000} to remove)")
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            amount = float(reply.content.strip())
            action = "Give" if amount > 0 else "Remove"
            view2 = ConfirmView(ctx, f"{action} {abs(amount):,.0f} {currency} to/from {member.mention}?")
            msg2 = await ctx.send(embed=warning_embed(f"{action} Currency", f"{action} {abs(amount):,.0f} {currency} {member.mention}?"), view=view2)
            await view2.wait()
            if view2.value:
                await db.add_user_balance(ctx.guild.id, member.id, currency, amount)
                await msg2.edit(embed=success_embed(f"{action}d", f"{action}d {abs(amount):,.0f} {currency} {member.mention}!"), view=None)
        except:
            pass

    @commands.command(name="ranks_coin")
    @has_any_power()
    async def ranks_coin(self, ctx):
        currencies = ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]
        emojis = ["💎", "💠", "👁️", "🐉"]
        view = CurrencySelectView(currencies, emojis)
        msg = await ctx.send(embed=info_embed("Currency Rankings", "Select currency:", private=True), view=view)
        await view.wait()
        if view.selected is None:
            return
        ranks = await db.get_user_ranks(ctx.guild.id, view.selected)
        sorted_ranks = sorted(ranks.items(), key=lambda x: x[1]["rank"])
        lines = []
        for uid, info in sorted_ranks[:20]:
            m = ctx.guild.get_member(uid)
            lines.append(f"{info['rank']}. {m.mention if m else f'<@{uid}>'} — {info['balance']:,.0f} {view.selected}")
        embed = info_embed(f"{view.selected} Leaderboard", "\n".join(lines) or "No data", private=True)
        await msg.edit(embed=embed, view=None)

    @commands.command(name="giftall")
    @has_any_power()
    async def giftall(self, ctx):
        currencies = ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]
        emojis = ["💎", "💠", "👁️", "🐉"]
        view = CurrencySelectView(currencies, emojis)
        msg = await ctx.send(embed=info_embed("Gift to Everyone", "Select currency:", private=True), view=view)
        await view.wait()
        if view.selected is None:
            return
        items = await db.get_shop_items(ctx.guild.id, view.selected)
        if not items:
            return await msg.edit(embed=error_embed("No items in shop"), view=None)
        lines = [f"{i+1}. {item['emoji'] or ''} {item['item_name']} — {item['price']:,.0f} {view.selected}" for i, item in enumerate(items)]
        embed = info_embed(f"{view.selected} Shop Items", "\n".join(lines), private=True)
        embed.set_footer(text="Type number, or use buttons")
        await msg.edit(embed=embed, view=ItemSelectView(items))
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            idx = int(reply.content.strip()) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                await ctx.send("How many to gift to everyone?")
                qty = int((await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)).content.strip())
                await ctx.send("Claim time limit? Type duration (e.g., 1h, 1d) or **none**.")
                duration_str = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)).content.strip()
                import time
                expires = 0
                if duration_str.lower() != "none":
                    import re
                    match = re.match(r"(\d+)([hdwm])", duration_str)
                    if match:
                        mult = {"h": 3600, "d": 86400, "w": 604800, "m": 2592000}
                        expires = time.time() + int(match.group(1)) * mult.get(match.group(2), 86400)
                view2 = ConfirmView(ctx, f"Gift {qty}x {item['item_name']} to EVERYONE?")
                msg2 = await ctx.send(embed=warning_embed("Gift All", f"Gift {qty}x {item['item_name']} to EVERYONE in server?"), view=view2)
                await view2.wait()
                if view2.value:
                    for m in ctx.guild.members:
                        if not m.bot:
                            await db.add_inventory(ctx.guild.id, m.id, item['item_name'], qty)
                    await msg2.edit(embed=success_embed("Gifted", f"Gifted {qty}x {item['item_name']} to everyone!"), view=None)
        except:
            pass

    @commands.command(name="autogift")
    @has_any_power()
    async def autogift(self, ctx, role: discord.Role = None):
        if not role:
            return await ctx.send(embed=error_embed("Usage: I?autogift @role"))
        currencies = ["Gems", "Crystal Shards", "Vanishing Orbs", "Dragon Coins"]
        emojis = ["💎", "💠", "👁️", "🐉"]
        view = CurrencySelectView(currencies, emojis)
        msg = await ctx.send(embed=info_embed("Auto Gift Setup", "Select currency:"), view=view)
        await view.wait()
        if view.selected is None:
            return
        items = await db.get_shop_items(ctx.guild.id, view.selected)
        if not items:
            return await msg.edit(embed=error_embed("No items"), view=None)
        lines = [f"{i+1}. {item['emoji'] or ''} {item['item_name']}" for i, item in enumerate(items)]
        await msg.edit(embed=info_embed("Which item?", "\n".join(lines)), view=None)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            idx = int(reply.content.strip()) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                await ctx.send("Amount?")
                amount = int((await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)).content.strip())
                await ctx.send("Time interval? (e.g., 1d, 7d, 1w)")
                interval_str = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)).content.strip()
                import re
                match = re.match(r"(\d+)([hdwm])", interval_str)
                if not match:
                    return await ctx.send(embed=error_embed("Invalid interval"))
                mult = {"h": 3600, "d": 86400, "w": 604800, "m": 2592000}
                interval = int(match.group(1)) * mult[match.group(2)]
                await ctx.send("Blacklist role? @role or **skip**.")
                bl_reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                bl_role = None
                if bl_reply.content.startswith("<@&"):
                    bl_role = int(bl_reply.content.strip("<@&>"))
                await db.db.execute(
                    "INSERT INTO auto_gifts (guild_id, role_id, currency, item_name, amount, interval_seconds, blacklist_role_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ctx.guild.id, role.id, view.selected, item['item_name'], amount, interval, bl_role))
                await db.db.commit()
                desc = f"Every {interval_str}, {role.mention} will receive {amount}x {item['item_name']}."
                if bl_role:
                    r = ctx.guild.get_role(bl_role)
                    desc += f"\n(except {r.mention if r else 'blacklisted'})"
                await ctx.send(embed=success_embed("Auto Gift Setup", desc))
        except:
            pass

    @commands.command(name="logs")
    @has_any_power()
    async def logs(self, ctx):
        embed = info_embed("Server Logs", "Select category:", private=True)
        msg = await ctx.send(embed=embed, view=LogSelectView())
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            log_type = reply.content.strip().lower()
            type_map = {"setup changes": "setup", "jail logs": "jail", "purchase logs": "purchase",
                        "transfer logs": "transfer", "punishment logs": "punishment", "all": None}
            lt = type_map.get(log_type)
            entries = await db.get_logs(ctx.guild.id, lt, 20)
            if not entries:
                return await msg.edit(embed=info_embed("Logs", "No entries found."), view=None)
            import time
            lines = []
            for e in entries:
                from datetime import datetime
                ts = datetime.fromtimestamp(e["created_at"]).strftime("%Y-%m-%d %H:%M")
                d = e["data"]
                lines.append(f"• {ts} — {d.get('text', str(d))}")
            embed = info_embed(f"{log_type.title()} Logs", "\n".join(lines[:20]), private=True)
            await msg.edit(embed=embed, view=None)
        except:
            pass

    @commands.command(name="config")
    @has_any_power()
    async def config_cmd(self, ctx):
        embed = info_embed("Server Config Commands",
            "**Jail System**\n• `I?jsetup` — Menu-based jail setup\n• `I?jsetup_all` — Wizard-based jail setup\n\n"
            "**Punishment System**\n• `I?psetup` — Menu-based punishment setup\n• `I?psetup_all` — Wizard-based punishment setup\n\n"
            "**Icon Role System**\n• `I?irsetup` — Menu-based icon role setup\n• `I?irsetup_all` — Wizard-based icon role setup\n\n"
            "**Reaction Role System**\n• `I?rrsetup` — Menu-based reaction role setup\n• `I?rrsetup_all` — Wizard-based reaction role setup\n\n"
            "**Group Reaction Role System**\n• `I?grrsetup` — Menu-based group RR setup\n• `I?grrsetup_all` — Wizard-based group RR setup\n\n"
            "**Economy System**\n• `I?esetup` — Menu-based economy setup\n• `I?esetup_all` — Wizard-based economy setup\n\n"
            "**Shop System**\n• `I?shopitems` — Menu-based shop setup\n• `I?shopitems_all` — Wizard-based shop setup\n\n"
            "**Gift System**\n• `I?gsetup` — Menu-based gift setup\n• `I?gsetup_all` — Wizard-based gift setup\n\n"
            "**Wallet Setup**\n• `I?wsetup` — Menu-based wallet setup\n• `I?wsetup_all` — Wizard-based wallet setup\n\n"
            "**Utility Commands**\n• `I?freeall` — Free all jailed users\n• `I?server_reset` — Reset all server data\n"
            "• `I?power @mention/-r` — Give/remove Power\n• `I?accmerge` — Merge accounts\n"
            "• `I?listaccmerge` — List merged accounts\n• `I?hecker @mention -y/-r` — Grant Hecker\n"
            "• `I?give_coin @user` — Give/remove currency\n• `I?ranks_coin` — Currency rankings\n"
            "• `I?giftall` — Gift items to everyone\n• `I?autogift @role` — Auto gift to role members\n"
            "• `I?logs` — View server logs")
        await ctx.send(embed=embed)


class ConfirmView(discord.ui.View):
    def __init__(self, ctx, question):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.question = question
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class CurrencySelectView(discord.ui.View):
    def __init__(self, currencies, emojis):
        super().__init__(timeout=60)
        self.selected = None
        for c, e in zip(currencies, emojis):
            self.add_item(CurrencyButton(c, e))

    async def on_button(self, interaction: discord.Interaction, currency: str):
        self.selected = currency
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class CurrencyButton(discord.ui.Button):
    def __init__(self, currency, emoji):
        super().__init__(label=f"{emoji} {currency}", style=discord.ButtonStyle.primary)
        self.currency = currency

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.selected = self.currency
        for child in view.children:
            child.disabled = True
        await interaction.response.edit_message(view=view)
        view.stop()


class ItemSelectView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=60)
        for i, item in enumerate(items[:5]):
            self.add_item(ItemButton(i, item))


class ItemButton(discord.ui.Button):
    def __init__(self, idx, item):
        super().__init__(label=f"{idx+1}. {item['item_name'][:20]}", style=discord.ButtonStyle.secondary)
        self.idx = idx

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Selected item {self.idx+1}", ephemeral=True)
        self.view.stop()


class LogSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        options = ["Setup Changes", "Jail Logs", "Purchase Logs", "Transfer Logs", "Punishment Logs", "All"]
        for o in options:
            self.add_item(LogButton(o))


class LogButton(discord.ui.Button):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.log_type = label

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Selected: {self.log_type}", ephemeral=True)
        self.view.stop()


async def setup(bot):
    await bot.add_cog(Owner(bot))

import discord
from discord.ext import commands
import time
import random
import json
import asyncio
from utils.database import db
from utils.checks import has_spower, has_any_power, is_owner_or_dev
from utils.embeds import *
from cogs.owner import ConfirmView, CurrencySelectView


class Jail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tasks_started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._tasks_started:
            self._tasks_started = True
            asyncio.create_task(self.check_jail_expirations())

    async def check_role_order(self, guild, author, target):
        config = await db.get_guild_config(guild.id, "jail_config", {})
        if not config.get("role_order_enabled"):
            return True
        order = config.get("role_order", [])
        if not order:
            return True
        author_top = author.top_role.position
        target_top = target.top_role.position
        if target_top >= author_top:
            return False
        unlocked = [r for r in order if r != "all"]
        if unlocked and not any(r.id in unlocked for r in author.roles):
            return False
        return True

    async def can_jail(self, guild, author, target):
        config = await db.get_guild_config(guild.id, "jail_config", {})
        if author.id == target.id:
            return False, "You cannot jail yourself!"
        if target.bot:
            return False, "You cannot jail the bot!"
        state = await db.get_jail_state(guild.id, author.id)
        if state and state[0] > time.time():
            return False, "You are currently jailed! You cannot jail others."
        if not await self.check_role_order(guild, author, target):
            return False, "Your role is not high enough to use jail."
        return True, None

    async def get_jail_message(self, guild_id, case_type):
        cursor = await db.db.execute(
            "SELECT message FROM jail_messages WHERE guild_id = ? AND case_type = ?",
            (guild_id, case_type))
        row = await cursor.fetchone()
        if row:
            return row[0]
        defaults = {
            "success": "[user] bribed the policemen and jailed [target] for [duration]",
            "pro_success": "[user] bribed the commissioner and jailed [target] for [duration]",
            "reverse": "[user] tried to jail [target], but [target] pulled out an UNO REVERSE and now [user] rot in jail for [duration]",
            "immunity": "[user] tried bribe and jail [target] but failed",
            "full_immunity": "[user] tried bribe and jail [target] but failed",
            "thief": "[user] tried to bribe and jail but failed",
            "free": "[target] has been released from jail after [duration]",
            "strike3": "[user] has got **Full Immunity** for 12 hours"
        }
        return defaults.get(case_type, "")

    def format_msg(self, msg, user, target, duration):
        return msg.replace("[user]", user).replace("[target]", target).replace("[duration]", duration)

    async def get_random_gif(self, case_type):
        cursor = await db.db.execute("SELECT url FROM jail_gifs WHERE case_type = ? ORDER BY RANDOM() LIMIT 1",
                                    (case_type,))
        row = await cursor.fetchone()
        return row[0] if row else None

    @commands.command(name="jail")
    async def jail(self, ctx, target: discord.Member = None, power: str = None):
        if not target:
            return await ctx.send(embed=error_embed("Usage: /jail @user [2min/5min/2min PRO/5min PRO]"))
        can, reason = await self.can_jail(ctx.guild, ctx.author, target)
        if not can:
            return await ctx.send(embed=error_embed(reason))

        is_pro = "PRO" in (power or "").upper()
        duration_str = power.replace(" PRO", "").replace(" pro", "").strip() if power else "2min"
        duration_map = {"2min": 120, "5min": 300}
        duration = duration_map.get(duration_str, 120)

        # Check Full Reverse Immunity
        cursor = await db.db.execute(
            "SELECT role_id, custom_message, gif_url FROM full_reverse_immunity_roles WHERE guild_id = ?",
            (ctx.guild.id,))
        for row in await cursor.fetchall():
            role = ctx.guild.get_role(row[0])
            if role and any(r.id == row[0] for r in target.roles):
                # REVERSE!
                msg_text = row[1] or await self.get_jail_message(ctx.guild.id, "reverse")
                gif_url = row[2] or await self.get_random_gif(3)
                await db.set_jail_state(ctx.guild.id, ctx.author.id, time.time() + duration, target.id, 0)
                embed = error_embed("Jail Reversed",
                    self.format_msg(msg_text, ctx.author.mention, target.mention, duration_str))
                if gif_url:
                    embed.set_image(url=gif_url)
                await ctx.send(embed=embed)
                await db.log_entry(ctx.guild.id, "jail", {"type": "reverse", "attacker": ctx.author.id,
                                                         "target": target.id, "duration": duration_str})
                return

        # Check card slots
        cursor = await db.db.execute(
            "SELECT item_name, expires_at FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = ? ORDER BY slot_num",
            (ctx.guild.id, target.id, "pro" if is_pro else "normal"))
        items = [(r[0], r[1]) for r in await cursor.fetchall() if r[1] > time.time()]
        # Also check normal slots if pro and empty
        if is_pro and not any(i[0] == "Full Immunity" for i in items):
            cursor = await db.db.execute(
                "SELECT item_name, expires_at FROM card_slots WHERE guild_id = ? AND user_id = ? AND slot_type = 'normal' ORDER BY slot_num",
                (ctx.guild.id, target.id))
            items = [(r[0], r[1]) for r in await cursor.fetchall() if r[1] > time.time()]

        for item_name, expires_at in items:
            if item_name == "Full Immunity":
                await db.remove_inventory(ctx.guild.id, target.id, "Full Immunity")
                await db.db.execute("DELETE FROM card_slots WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                                   (ctx.guild.id, target.id, "Full Immunity"))
                await db.db.commit()
                gif = await self.get_random_gif(5)
                embed = error_embed("Full Immunity",
                    self.format_msg(await self.get_jail_message(ctx.guild.id, "full_immunity"),
                                   ctx.author.mention, target.mention, duration_str))
                if gif:
                    embed.set_image(url=gif)
                return await ctx.send(embed=embed)
            elif item_name == "Immunity" and not is_pro:
                await db.remove_inventory(ctx.guild.id, target.id, "Immunity")
                await db.db.execute("DELETE FROM card_slots WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                                   (ctx.guild.id, target.id, "Immunity"))
                await db.db.commit()
                gif = await self.get_random_gif(4)
                embed = error_embed("Immune",
                    self.format_msg(await self.get_jail_message(ctx.guild.id, "immunity"),
                                   ctx.author.mention, target.mention, duration_str))
                if gif:
                    embed.set_image(url=gif)
                return await ctx.send(embed=embed)
            elif item_name == "Reverse" and not is_pro:
                await db.remove_inventory(ctx.guild.id, target.id, "Reverse")
                await db.db.execute("DELETE FROM card_slots WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                                   (ctx.guild.id, target.id, "Reverse"))
                await db.db.commit()
                await db.set_jail_state(ctx.guild.id, ctx.author.id, time.time() + duration, target.id, 0)
                gif = await self.get_random_gif(3)
                msg_text = await self.get_jail_message(ctx.guild.id, "reverse")
                embed = error_embed("Jail Reversed",
                    self.format_msg(msg_text, ctx.author.mention, target.mention, duration_str))
                if gif:
                    embed.set_image(url=gif)
                return await ctx.send(embed=embed)
            elif item_name == "Mysterious Thief" and not is_pro:
                await db.remove_inventory(ctx.guild.id, target.id, "Mysterious Thief")
                await db.db.execute("DELETE FROM card_slots WHERE guild_id = ? AND user_id = ? AND item_name = ?",
                                   (ctx.guild.id, target.id, "Mysterious Thief"))
                await db.db.commit()
                await db.set_jail_state(ctx.guild.id, ctx.author.id, time.time() + duration, target.id, 0)
                gif = await self.get_random_gif(6)
                embed = error_embed("Mysterious Thief",
                    self.format_msg(await self.get_jail_message(ctx.guild.id, "thief"),
                                   ctx.author.mention, "A Mysterious Person", duration_str))
                if gif:
                    embed.set_image(url=gif)
                return await ctx.send(embed=embed)
            break

        # SUCCESS - jail the target
        await db.set_jail_state(ctx.guild.id, target.id, time.time() + duration, ctx.author.id, 1 if is_pro else 0)
        case = "pro_success" if is_pro else "success"
        gif = await self.get_random_gif(1 if not is_pro else 2)
        embed = success_embed("Jailed",
            self.format_msg(await self.get_jail_message(ctx.guild.id, case),
                           ctx.author.mention, target.mention, duration_str))
        if gif:
            embed.set_image(url=gif)
        await ctx.send(embed=embed)
        await db.log_entry(ctx.guild.id, "jail", {"type": "success", "attacker": ctx.author.id,
                                                 "target": target.id, "duration": duration_str, "pro": is_pro})

        # Strike tracking
        strike_triggered, fi_until = await db.increment_strike(ctx.guild.id, target.id)
        if strike_triggered and fi_until:
            await db.db.execute(
                "INSERT OR REPLACE INTO strike_tracking (guild_id, user_id, strike_count, full_immunity_until) VALUES (?, ?, 0, ?)",
                (ctx.guild.id, target.id, fi_until))
            await db.db.commit()
            embed2 = warning_embed("Full Immunity Gained",
                self.format_msg(await self.get_jail_message(ctx.guild.id, "strike3"),
                               target.mention, "", "12 hours"))
            await ctx.send(embed=embed2)

    async def check_jail_expirations(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = time.time()
                cursor = await db.db.execute(
                    "SELECT guild_id, user_id, jailer_id FROM jail_state WHERE jailed_until <= ?", (now,))
                for row in await cursor.fetchall():
                    guild_id, user_id, jailer_id = row
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    member = guild.get_member(user_id)
                    await db.remove_jail_state(guild_id, user_id)
                    if member:
                        config = await db.get_guild_config(guild_id, "jail_config", {})
                        silence_role = guild.get_role(config.get("silence_role_id"))
                        if silence_role and silence_role in member.roles:
                            await member.remove_roles(silence_role, reason="Jail expired")
                        gif = await self.get_random_gif(7)
                        msg = await self.get_jail_message(guild_id, "free")
                        embed = success_embed("Released",
                            self.format_msg(msg, "", member.mention, ""))
                        if gif:
                            embed.set_image(url=gif)
                        log_channel = guild.get_channel(config.get("log_channel_id"))
                        if log_channel:
                            await log_channel.send(embed=embed)
            except Exception as e:
                print(f"Jail expiration check error: {e}")
            await asyncio.sleep(30)

    @commands.command(name="jsetup")
    @has_spower()
    async def jsetup(self, ctx):
        embed = info_embed("Jail Setup Menu",
            "What would you like to configure?\n\n"
            "1. Silence Role\n2. Log Channel\n3. Full Reverse Immunity Roles\n"
            "4. Full Immunity Roles\n5. Role Order\n\nType the number, or **done**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            choice = reply.content.strip()
            if choice == "1":
                await ctx.send("Reply with @role or **skip**.")
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.startswith("<@&"):
                    role_id = int(r.content.strip("<@&>"))
                    config = await db.get_guild_config(ctx.guild.id, "jail_config", {})
                    config["silence_role_id"] = role_id
                    await db.set_guild_config(ctx.guild.id, "jail_config", config)
                    await ctx.send(embed=success_embed("Silence role set"))
            elif choice == "2":
                await ctx.send("Reply with #channel or **skip**.")
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.startswith("<#"):
                    ch_id = int(r.content.strip("<#>"))
                    config = await db.get_guild_config(ctx.guild.id, "jail_config", {})
                    config["log_channel_id"] = ch_id
                    await db.set_guild_config(ctx.guild.id, "jail_config", config)
                    await ctx.send(embed=success_embed("Log channel set"))
            elif choice == "3":
                await ctx.send("Reply with @role to add, **remove** to remove, **done** to finish.")
            elif choice == "5":
                await ctx.send("Reply **-y** to set up role order.")
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.strip() == "-y":
                    await ctx.send("What is the **highest** role that can use jail? Reply with @role.")
                    r2 = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                    if r2.content.startswith("<@&"):
                        order = [int(r2.content.strip("<@&>"))]
                        await ctx.send("Add role below? @role or **all** for everyone, or **done**.")
                        while True:
                            r3 = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                            if r3.content.strip().lower() == "done":
                                break
                            elif r3.content.strip().lower() == "all":
                                order.append("all")
                                break
                            elif r3.content.startswith("<@&"):
                                order.append(int(r3.content.strip("<@&>")))
                            await ctx.send("Add another? @role, **all**, or **done**.")
                        config = await db.get_guild_config(ctx.guild.id, "jail_config", {})
                        config["role_order"] = order
                        config["role_order_enabled"] = True
                        await db.set_guild_config(ctx.guild.id, "jail_config", config)
                        await ctx.send(embed=success_embed("Role order set!"))
        except:
            pass

    @commands.command(name="jsetup_all")
    @has_spower()
    async def jsetup_all(self, ctx):
        embed = info_embed("Jail Setup Wizard",
            "Welcome! I'll guide you through setting up the jail system.")
        view = ConfirmView(ctx, "Start setup?")
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if not view.value:
            return
        await msg.edit(embed=info_embed("Step 1", "Which role should be given to jailed users?\nReply with @role or **skip**."), view=None)
        try:
            r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            config = {}
            if r.content.startswith("<@&"):
                config["silence_role_id"] = int(r.content.strip("<@&>"))
            await ctx.send(embed=info_embed("Step 2", "In which channel should jail logs be posted?\nReply with #channel or **skip**."))
            r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if r.content.startswith("<#"):
                config["log_channel_id"] = int(r.content.strip("<#>"))
            await db.set_guild_config(ctx.guild.id, "jail_config", config)
            await ctx.send(embed=success_embed("Setup complete!"))
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="djsetup")
    @is_owner_or_dev()
    async def djsetup(self, ctx):
        embed = info_embed("Dev Jail Setup (GLOBAL)",
            "1. Default Jail Messages\n2. Default Effect Durations\n"
            "3. Default Shop Item Descriptions\n4. Enable/Disable Logs\n"
            "5. Log Destination (Channel/DM/Disable)\n6. Enable/Disable GIFs\n"
            "7. Mysterious Thief Message\n8. Failed Jail Message\n"
            "9. Server-Specific Settings\n\nType number or **done**.")
        await ctx.send(embed=embed)

    @commands.command(name="gifsetup_all")
    @is_owner_or_dev()
    async def gifsetup_all(self, ctx):
        embed = info_embed("GIF Setup for Jail Logs (GLOBAL)",
            "Reply with GIF link, or type number to edit existing case.\n\n"
            "Cases:\n1. Normal jail success\n2. Pro jail success\n"
            "3. Reverse jail\n4. Immunity block\n5. Full Immunity block\n"
            "6. Mysterious Thief\n7. Free from jail\n\n"
            "Type number to edit, new link to add, or **done**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            content = reply.content.strip()
            if content.isdigit():
                case = int(content)
                await ctx.send("Reply with a GIF URL.")
                url = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await db.db.execute("INSERT INTO jail_gifs (case_type, url) VALUES (?, ?)", (case, url))
                await db.db.commit()
                await ctx.send(embed=success_embed(f"GIF added for case {case}"))
            elif content.startswith("http"):
                await ctx.send("Which case number?")
                case = int((await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip())
                await db.db.execute("INSERT INTO jail_gifs (case_type, url) VALUES (?, ?)", (case, content))
                await db.db.commit()
                await ctx.send(embed=success_embed(f"GIF added for case {case}"))
        except:
            pass

    @commands.command(name="gifsetup_reset")
    @is_owner_or_dev()
    async def gifsetup_reset(self, ctx):
        view = ConfirmView(ctx, "Reset ALL GIFs? This affects ALL servers.")
        msg = await ctx.send(embed=warning_embed("Reset GIFs", "Reset ALL GIFs?"), view=view)
        await view.wait()
        if view.value:
            await db.db.execute("DELETE FROM jail_gifs")
            await db.db.commit()
            await msg.edit(embed=success_embed("GIFs Reset", "All GIFs have been reset."), view=None)

    @commands.command(name="gifsetup_list")
    @is_owner_or_dev()
    async def gifsetup_list(self, ctx):
        labels = ["Normal Success", "Pro Success", "Reverse", "Immunity Block",
                  "Full Immunity Block", "Mysterious Thief", "Free from Jail"]
        lines = []
        for i, label in enumerate(labels, 1):
            cursor = await db.db.execute("SELECT COUNT(*) FROM jail_gifs WHERE case_type = ?", (i,))
            count = (await cursor.fetchone())[0]
            lines.append(f"Case {i} ({label}): {'✅' if count > 0 else '❌'} {count} GIF{'s' if count != 1 else ''}")
        embed = info_embed("GIF List (GLOBAL)", "\n".join(lines))
        await ctx.send(embed=embed)

    @commands.command(name="gcsetup")
    @is_owner_or_dev()
    async def gcsetup(self, ctx):
        embed = info_embed("Global Coin Setup",
            "Enable global currency?\nReply **-y** or **-n**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip().lower()
            if reply == "-y":
                await ctx.send("Currency name?")
                name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await ctx.send("Emoji?")
                emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await ctx.send("Min-Max per minute per message?")
                mm = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await db.set_global_config("global_currency", {"name": name, "emoji": emoji,
                    "min_msg": int(mm.split()[0]), "max_msg": int(mm.split()[1]) if " " in mm else 0})
                await ctx.send(embed=success_embed(f"{name} {emoji} enabled!"))
        except:
            pass


async def setup(bot):
    import asyncio
    await bot.add_cog(Jail(bot))

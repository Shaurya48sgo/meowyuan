import discord
from discord.ext import commands
import time
import random
import asyncio
from utils.database import db
from utils.embeds import *


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        await db.ensure_user(member.guild.id, member.id)
        iconroles_cog = self.bot.get_cog("IconRoles")
        if iconroles_cog:
            await iconroles_cog.update_icon_role(member)

        # Auto gifts
        cursor = await db.db.execute(
            "SELECT item_name, amount FROM auto_gifts WHERE guild_id = ? AND role_id = ?",
            (member.guild.id, member.id))
        # Also check if member has any matching auto-gift roles
        cursor2 = await db.db.execute(
            "SELECT item_name, amount, blacklist_role_id FROM auto_gifts WHERE guild_id = ?",
            (member.guild.id,))
        for name, amount, bl_role_id in await cursor2.fetchall():
            if bl_role_id:
                bl_role = member.guild.get_role(bl_role_id)
                if bl_role and bl_role in member.roles:
                    continue
            cursor3 = await db.db.execute(
                "SELECT role_id FROM auto_gifts WHERE guild_id = ? AND item_name = ? AND amount = ?",
                (member.guild.id, name, amount))
            for row in await cursor3.fetchall():
                role = member.guild.get_role(row[0])
                if role and role in member.roles:
                    await db.add_inventory(member.guild.id, member.id, name, amount)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            iconroles_cog = self.bot.get_cog("IconRoles")
            if iconroles_cog:
                await iconroles_cog.update_icon_role(after)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # Don't process commands here

        # Economy earnings
        config = await db.get_guild_config(message.guild.id, "economy_config", {})
        currencies = config.get("currencies", {})
        earning = config.get("earning", {})

        # Message earning
        for cur in currencies:
            cur_earning = earning.get(cur, {})
            msg_min = cur_earning.get("message_min", 0)
            msg_max = cur_earning.get("message_max", 0)
            if msg_min > 0 and msg_max > 0:
                # Check blacklist roles
                cursor = await db.db.execute(
                    "SELECT role_id FROM earning_blacklist_roles WHERE guild_id = ? AND earning_type = 'message'",
                    (message.guild.id,))
                bl_roles = {r[0] for r in await cursor.fetchall()}
                if any(r.id in bl_roles for r in message.author.roles):
                    continue

                # Check blacklist channels
                cursor = await db.db.execute(
                    "SELECT channel_id FROM earning_blacklist_channels WHERE guild_id = ? AND earning_type = 'message'",
                    (message.guild.id,))
                bl_channels = {r[0] for r in await cursor.fetchall()}
                if message.channel.id in bl_channels:
                    continue

                amount = random.uniform(msg_min, msg_max)
                # Apply boosts
                amount = await self.apply_boosts(message.guild.id, message.author, cur, "message", amount)
                await db.add_user_balance(message.guild.id, message.author.id, cur, amount)

    async def apply_boosts(self, guild_id, member, currency, earning_type, base_amount):
        cursor = await db.db.execute(
            "SELECT boost_type, target_id, target_type, percentage FROM boost_config WHERE guild_id = ? AND currency = ? AND earning_type = ?",
            (guild_id, currency, earning_type))
        multiplier = 1.0
        for boost_type, target_id, target_type, pct in await cursor.fetchall():
            if boost_type == "role" and target_type == "role" and any(r.id == target_id for r in member.roles):
                multiplier += pct / 100
            elif boost_type == "channel" and target_type == "channel":
                # Handled elsewhere
                pass
            elif boost_type == "currency_role" and target_type == "role" and any(r.id == target_id for r in member.roles):
                multiplier += pct / 100
            elif boost_type == "multi" and target_type == "role" and any(r.id == target_id for r in member.roles):
                multiplier += pct / 100
        return base_amount * multiplier

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if after.channel and (not before.channel or before.channel != after.channel):
            # Joined VC - start tracking
            await db.db.execute(
                "INSERT OR REPLACE INTO earned_vc (guild_id, user_id, last_minute) VALUES (?, ?, ?)",
                (member.guild.id, member.id, int(time.time() // 60)))
            await db.db.commit()
        elif not after.channel and before.channel:
            # Left VC - stop tracking
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Check if reaction was from the bot (we don't want to earn from bot's own reactions)
        config = await db.get_guild_config(guild.id, "economy_config", {})
        currencies = config.get("currencies", {})

        for cur in currencies:
            cur_earning = config.get("earning", {}).get(cur, {})
            react_rate = cur_earning.get("reaction_rate", 0)
            if react_rate > 0:
                cursor = await db.db.execute(
                    "SELECT role_id FROM earning_blacklist_roles WHERE guild_id = ? AND earning_type = 'reaction'",
                    (guild.id,))
                bl_roles = {r[0] for r in await cursor.fetchall()}
                if any(r.id in bl_roles for r in member.roles):
                    continue

                cursor = await db.db.execute(
                    "SELECT channel_id FROM earning_blacklist_channels WHERE guild_id = ? AND earning_type = 'reaction'",
                    (guild.id,))
                bl_channels = {r[0] for r in await cursor.fetchall()}
                if payload.channel_id in bl_channels:
                    continue

                # Check for duplicate reactions (reacting, removing, re-reacting = ONE)
                cursor = await db.db.execute(
                    "SELECT 1 FROM earned_reactions WHERE guild_id = ? AND user_id = ? AND message_id = ?",
                    (guild.id, member.id, payload.message_id))
                if await cursor.fetchone():
                    continue

                amount = react_rate * random.uniform(0.5, 1.5)
                await db.add_user_balance(guild.id, member.id, cur, amount)
                await db.db.execute(
                    "INSERT OR IGNORE INTO earned_reactions (guild_id, user_id, message_id) VALUES (?, ?, ?)",
                    (guild.id, member.id, payload.message_id))
                await db.db.commit()

    async def cog_load(self):
        self.bot.loop.create_task(self.vc_earning_loop())

    async def vc_earning_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = int(time.time() // 60)
                cursor = await db.db.execute("SELECT guild_id, user_id, last_minute FROM earned_vc")
                for guild_id, user_id, last_minute in await cursor.fetchall():
                    if now <= last_minute:
                        continue
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    member = guild.get_member(user_id)
                    if not member or not member.voice or not member.voice.channel:
                        continue

                    config = await db.get_guild_config(guild_id, "economy_config", {})
                    currencies = config.get("currencies", {})
                    for cur in currencies:
                        cur_earning = config.get("earning", {}).get(cur, {})
                        vc_min = cur_earning.get("vc_min", 0)
                        vc_max = cur_earning.get("vc_max", 0)
                        if vc_min > 0 and vc_max > 0:
                            cursor2 = await db.db.execute(
                                "SELECT role_id FROM earning_blacklist_roles WHERE guild_id = ? AND earning_type = 'vc'",
                                (guild_id,))
                            bl_roles = {r[0] for r in await cursor2.fetchall()}
                            if any(r.id in bl_roles for r in member.roles):
                                continue

                            cursor2 = await db.db.execute(
                                "SELECT channel_id FROM earning_blacklist_channels WHERE guild_id = ? AND earning_type = 'vc'",
                                (guild_id,))
                            bl_channels = {r[0] for r in await cursor2.fetchall()}
                            if member.voice.channel.id in bl_channels:
                                continue

                            amount = random.uniform(vc_min, vc_max)
                            await db.add_user_balance(guild_id, member.id, cur, amount)

                    await db.db.execute(
                        "UPDATE earned_vc SET last_minute = ? WHERE guild_id = ? AND user_id = ?",
                        (now, guild_id, user_id))
                await db.db.commit()
            except Exception as e:
                print(f"VC earning loop error: {e}")
            await asyncio.sleep(60)


async def setup(bot):
    await bot.add_cog(Events(bot))

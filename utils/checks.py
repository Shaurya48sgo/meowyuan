from discord.ext import commands
from utils.database import db


def is_owner_or_dev():
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        if await db.is_global_dev(ctx.author.id):
            return True
        return False
    return commands.check(predicate)


def has_spower():
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        if await db.is_global_dev(ctx.author.id):
            return True
        if ctx.guild and await db.has_spower(ctx.guild.id, ctx.author.id):
            return True
        lock = await db.get_global_config("power_lock", False)
        if not lock and ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        return False
    return commands.check(predicate)


def has_power():
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        if await db.is_global_dev(ctx.author.id):
            return True
        if ctx.guild:
            if await db.has_power(ctx.guild.id, ctx.author.id):
                return True
            cursor = await db.db.execute(
                "SELECT role_id FROM power_roles WHERE guild_id = ?", (ctx.guild.id,))
            for row in await cursor.fetchall():
                if any(r.id == row[0] for r in ctx.author.roles):
                    return True
        return False
    return commands.check(predicate)


def has_any_power():
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        if await db.is_global_dev(ctx.author.id):
            return True
        if ctx.guild:
            if await db.has_power(ctx.guild.id, ctx.author.id):
                return True
            cursor = await db.db.execute(
                "SELECT role_id FROM power_roles WHERE guild_id = ?", (ctx.guild.id,))
            for row in await cursor.fetchall():
                if any(r.id == row[0] for r in ctx.author.roles):
                    return True
        return False
    return commands.check(predicate)


def has_mod_role():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if ctx.guild:
            cursor = await db.db.execute(
                "SELECT value FROM guild_config WHERE guild_id = ? AND key = 'mod_roles'",
                (ctx.guild.id,))
            row = await cursor.fetchone()
            if row:
                import json
                mod_roles = json.loads(row[0])
                if any(r.id in mod_roles for r in ctx.author.roles):
                    return True
        return False
    return commands.check(predicate)

import discord
from discord.ext import commands
import asyncio
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *
from cogs.owner import ConfirmView


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tasks_started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._tasks_started:
            self._tasks_started = True
            asyncio.create_task(self.check_temp_roles())

    @commands.command(name="easysetup_all")
    @has_spower()
    async def easysetup_all(self, ctx):
        embed = info_embed("Easy Setup Wizard",
            "I'll guide you through ALL systems.")
        await ctx.send(embed=embed)

        systems = [
            ("Jail System", "jsetup_all"),
            ("Punishment System", "psetup_all"),
            ("Icon Role System", "irsetup_all"),
            ("Reaction Roles", "rrsetup_all"),
            ("Group Reaction Roles", "grrsetup_all"),
            ("Economy System", "esetup_all"),
            ("Shop System", "shopitems_all"),
            ("Gift System", "gsetup_all"),
        ]

        for name, cmd_name in systems:
            await ctx.send(embed=info_embed(f"Setup {name}?", "Reply **-y** to setup or **-n** to skip."))
            try:
                reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                if reply.content.strip().lower() == "-y":
                    cmd = self.bot.get_command(cmd_name)
                    if cmd:
                        await ctx.invoke(cmd)
            except:
                pass

        await ctx.send(embed=success_embed("Easy setup complete! All systems configured."))

    @commands.command(name="easysetup")
    @has_spower()
    async def easysetup(self, ctx):
        embed = info_embed("Easy Setup Menu",
            "1. Jail System\n2. Punishment System\n3. Icon Role System\n"
            "4. Reaction Roles\n5. Group Reaction Roles\n6. Economy System\n"
            "7. Shop System\n8. Gift System\n9. Wallet Setup\n\n"
            "Type number or **done**.")
        await ctx.send(embed=embed)

    async def check_temp_roles(self):
        await self.bot.wait_until_ready()
        import time
        while not self.bot.is_closed():
            try:
                now = time.time()
                cursor = await db.db.execute(
                    "SELECT guild_id, user_id, role_id FROM temp_role_assignments WHERE expires_at <= ?",
                    (now,))
                for guild_id, user_id, role_id in await cursor.fetchall():
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    member = guild.get_member(user_id)
                    if member:
                        role = guild.get_role(role_id)
                        if role and role in member.roles:
                            await member.remove_roles(role, reason="Temp role expired")
                    await db.db.execute(
                        "DELETE FROM temp_role_assignments WHERE guild_id = ? AND user_id = ? AND role_id = ?",
                        (guild_id, user_id, role_id))
                await db.db.commit()
            except Exception as e:
                print(f"Temp role check error: {e}")
            await asyncio.sleep(60)


async def setup(bot):
    import asyncio
    await bot.add_cog(Admin(bot))

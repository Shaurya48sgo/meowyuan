import discord
from discord.ext import commands
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *


class IconRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="irsetup_all")
    @has_spower()
    async def irsetup_all(self, ctx):
        embed = info_embed("Icon Role Setup", "Which role has an icon role?\nReply with @role or **skip**.")
        msg = await ctx.send(embed=embed)
        try:
            while True:
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.strip().lower() == "skip":
                    break
                if r.content.startswith("<@&"):
                    role_id = int(r.content.strip("<@&>"))
                    await ctx.send("What is the icon role for this role? Reply with @icon_role.")
                    r2 = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                    if r2.content.startswith("<@&"):
                        icon_id = int(r2.content.strip("<@&>"))
                        await db.db.execute(
                            "INSERT OR REPLACE INTO icon_role_mappings (guild_id, role_id, icon_role_id) VALUES (?, ?, ?)",
                            (ctx.guild.id, role_id, icon_id))
                        await db.db.commit()
                        await ctx.send(embed=success_embed(f"Role mapped! {r.content} → {r2.content}"))
                        await ctx.send("Add another role? @role or **skip**.")

            await ctx.send(embed=info_embed("Which role IS an icon role?\nReply with @role or **skip**."))
            while True:
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                if r.content.strip().lower() == "skip":
                    break
                if r.content.startswith("<@&"):
                    role_id = int(r.content.strip("<@&>"))
                    await db.db.execute(
                        "INSERT OR IGNORE INTO icon_roles (guild_id, role_id) VALUES (?, ?)",
                        (ctx.guild.id, role_id))
                    await db.db.commit()
                    await ctx.send(embed=success_embed(f"{r.content} registered as icon role."))
                    await ctx.send("Add another? @role or **skip**.")

            await ctx.send(embed=success_embed("Icon Role Setup complete!"))
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="irsetup")
    @has_spower()
    async def irsetup(self, ctx):
        embed = info_embed("Icon Role Menu",
            "1. Add Role → Icon mapping\n2. Remove Role → Icon mapping\n"
            "3. Add Icon Role\n4. Remove Icon Role\n5. List All Mappings\n"
            "6. List All Icon Roles\n\nType number or **done**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if reply.content.strip() == "5":
                cursor = await db.db.execute(
                    "SELECT role_id, icon_role_id FROM icon_role_mappings WHERE guild_id = ?",
                    (ctx.guild.id,))
                rows = await cursor.fetchall()
                lines = []
                for role_id, icon_id in rows:
                    r = ctx.guild.get_role(role_id)
                    ir = ctx.guild.get_role(icon_id)
                    lines.append(f"{r.mention if r else f'<@&{role_id}>'} → {ir.mention if ir else f'<@&{icon_id}>'}")
                embed2 = info_embed("Role → Icon Mappings", "\n".join(lines) or "No mappings")
                await msg.edit(embed=embed2, view=None)
            elif reply.content.strip() == "6":
                cursor = await db.db.execute("SELECT role_id FROM icon_roles WHERE guild_id = ?", (ctx.guild.id,))
                rows = await cursor.fetchall()
                lines = [f"{ctx.guild.get_role(r[0]).mention if ctx.guild.get_role(r[0]) else f'<@&{r[0]}>'}" for r in rows]
                embed2 = info_embed("Registered Icon Roles", "\n".join(lines) or "None")
                await msg.edit(embed=embed2, view=None)
        except:
            pass

    async def update_icon_role(self, member: discord.Member):
        cursor = await db.db.execute(
            "SELECT icon_role_id FROM icon_role_mappings WHERE guild_id = ? AND role_id IN (SELECT value FROM json_each(?))",
            (member.guild.id, "[{}]".format(",".join(str(r.id) for r in member.roles))))
        icon_ids = {r[0] for r in await cursor.fetchall()}

        cursor = await db.db.execute(
            "SELECT role_id FROM icon_roles WHERE guild_id = ?", (member.guild.id,))
        valid_icons = {r[0] for r in await cursor.fetchall()}

        for icon_id in icon_ids:
            if icon_id in valid_icons:
                role = member.guild.get_role(icon_id)
                if role and role not in member.roles:
                    await member.add_roles(role, reason="Icon role update")
                    try:
                        await member.send(embed=info_embed("Icon Role Updated",
                            f"You now qualify for {role.mention}!\nYour icon has been automatically updated."))
                    except:
                        pass

        # Remove icon roles no longer qualified
        for icon_id in valid_icons:
            role = member.guild.get_role(icon_id)
            if role and role in member.roles and icon_id not in icon_ids:
                await member.remove_roles(role, reason="Icon role removed")


async def setup(bot):
    await bot.add_cog(IconRoles(bot))

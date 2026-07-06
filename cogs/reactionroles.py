import discord
from discord.ext import commands
from utils.database import db
from utils.checks import has_spower
from utils.embeds import *


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        # Check reaction roles
        cursor = await db.db.execute(
            "SELECT role_id FROM reaction_role_entries WHERE guild_id = ? AND message_id = ? AND emoji = ?",
            (guild.id, payload.message_id, str(payload.emoji)))
        row = await cursor.fetchone()
        if row:
            role = guild.get_role(row[0])
            if role and role not in member.roles:
                # Check group limits
                cursor2 = await db.db.execute(
                    "SELECT group_name, max_roles FROM group_reaction_roles WHERE guild_id = ?",
                    (guild.id,))
                for grp in await cursor2.fetchall():
                    cursor3 = await db.db.execute(
                        "SELECT role_id FROM grr_roles WHERE guild_id = ? AND group_name = ?",
                        (guild.id, grp[0]))
                    grp_roles = {r[0] for r in await cursor3.fetchall()}
                    if row[0] in grp_roles:
                        # Check ignore roles
                        cursor4 = await db.db.execute(
                            "SELECT role_id FROM grr_ignore_roles WHERE guild_id = ? AND group_name = ?",
                            (guild.id, grp[0]))
                        for ign in await cursor4.fetchall():
                            ign_role = guild.get_role(ign[0])
                            if ign_role and ign_role in member.roles:
                                return
                        # Check required roles
                        cursor5 = await db.db.execute(
                            "SELECT role_id FROM grr_required_roles WHERE guild_id = ? AND group_name = ?",
                            (guild.id, grp[0]))
                        required = {r[0] for r in await cursor5.fetchall()}
                        if required:
                            has_required = any(r.id in required for r in member.roles)
                            if not has_required:
                                return
                        # Check max roles limit
                        existing = [r for r in member.roles if r.id in grp_roles]
                        if len(existing) >= grp[1]:
                            await member.remove_roles(role, reason="Group RR limit")
                            # Remove the reaction
                            try:
                                channel = guild.get_channel(payload.channel_id)
                                if channel:
                                    msg = await channel.fetch_message(payload.message_id)
                                    await msg.remove_reaction(payload.emoji, member)
                            except:
                                pass
                            return
                try:
                    await member.add_roles(role, reason="Reaction role")
                except:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        cursor = await db.db.execute(
            "SELECT role_id FROM reaction_role_entries WHERE guild_id = ? AND message_id = ? AND emoji = ?",
            (guild.id, payload.message_id, str(payload.emoji)))
        row = await cursor.fetchone()
        if row:
            role = guild.get_role(row[0])
            if role and role in member.roles:
                await member.remove_roles(role, reason="Reaction role removed")

    @commands.command(name="rrsetup_all")
    @has_spower()
    async def rrsetup_all(self, ctx):
        embed = info_embed("Reaction Role Setup", "Which channel? #channel (required)")
        msg = await ctx.send(embed=embed)
        try:
            r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if not r.content.startswith("<#"):
                return
            channel_id = int(r.content.strip("<#>"))
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                return await ctx.send(embed=error_embed("Channel not found!"))

            await ctx.send("Message title?")
            title = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()

            roles_data = []
            while True:
                await ctx.send("Which role to add? @role, **make role**, or **done**.")
                r = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                content = r.content.strip()
                if content.lower() == "done":
                    break
                if content.lower() == "make role":
                    await ctx.send("Role name?")
                    name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                    role = await ctx.guild.create_role(name=name, reason="Reaction role")
                    await ctx.send(f"Created {role.mention}!")
                elif content.startswith("<@&"):
                    role = ctx.guild.get_role(int(content.strip("<@&>")))
                else:
                    continue

                await ctx.send(f"Emoji for {role.mention}?")
                emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                roles_data.append((role.id, emoji))

            # Create the message
            desc_lines = [f"{emoji} {ctx.guild.get_role(rid).mention if ctx.guild.get_role(rid) else f'<@&{rid}>'}" for rid, emoji in roles_data]
            embed2 = info_embed(title, "\n".join(desc_lines))
            msg2 = await channel.send(embed=embed2)
            for rid, emoji in roles_data:
                try:
                    await msg2.add_reaction(emoji)
                except:
                    await ctx.send(f"Failed to add reaction {emoji}")

            await db.db.execute(
                "INSERT OR REPLACE INTO reaction_role_messages (guild_id, channel_id, message_id, title) VALUES (?, ?, ?, ?)",
                (ctx.guild.id, channel_id, msg2.id, title))
            for rid, emoji in roles_data:
                await db.db.execute(
                    "INSERT OR REPLACE INTO reaction_role_entries (guild_id, message_id, role_id, emoji) VALUES (?, ?, ?, ?)",
                    (ctx.guild.id, msg2.id, rid, emoji))
            await db.db.commit()
            await ctx.send(embed=success_embed("Reaction role message posted!"))
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="rrsetup")
    @has_spower()
    async def rrsetup(self, ctx):
        embed = info_embed("Reaction Role Menu",
            "1. Create New Message\n2. Edit Existing\n3. Delete\n\nType number or **done**.")
        await ctx.send(embed=embed)

    @commands.command(name="grrsetup_all")
    @has_spower()
    async def grrsetup_all(self, ctx):
        embed = info_embed("Group Reaction Role Setup", "Group name?")
        msg = await ctx.send(embed=embed)
        try:
            name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            await ctx.send("Max roles from this group? (number)")
            max_r = int((await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip())

            await db.db.execute(
                "INSERT OR REPLACE INTO group_reaction_roles (guild_id, group_name, max_roles) VALUES (?, ?, ?)",
                (ctx.guild.id, name, max_r))
            await db.db.commit()

            while True:
                await ctx.send("Role to add? Reply **-y** for existing role, **auto make** to create, or **done**.")
                r = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip().lower()
                if r == "done":
                    break
                if r == "auto make":
                    await ctx.send("Role name?")
                    rname = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                    role = await ctx.guild.create_role(name=rname, reason="GRR")
                    await ctx.send(f"Created {role.mention}!")
                    await ctx.send("Emoji?")
                    emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                    await db.db.execute(
                        "INSERT OR REPLACE INTO grr_roles (guild_id, group_name, role_id, emoji) VALUES (?, ?, ?, ?)",
                        (ctx.guild.id, name, role.id, emoji))
                elif r.startswith("<@&"):
                    role_id = int(r.strip("<@&>"))
                    await ctx.send("Emoji?")
                    emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                    await db.db.execute(
                        "INSERT OR REPLACE INTO grr_roles (guild_id, group_name, role_id, emoji) VALUES (?, ?, ?, ?)",
                        (ctx.guild.id, name, role_id, emoji))
                await db.db.commit()

            await ctx.send(embed=success_embed(f"Group \"{name}\" created!"))
        except:
            await ctx.send(embed=error_embed("Setup timed out."))

    @commands.command(name="grrlist")
    @has_spower()
    async def grrlist(self, ctx):
        cursor = await db.db.execute(
            "SELECT group_name, max_roles FROM group_reaction_roles WHERE guild_id = ?",
            (ctx.guild.id,))
        embed = info_embed("Group Reaction Roles")
        for row in await cursor.fetchall():
            name, max_r = row
            cursor2 = await db.db.execute(
                "SELECT role_id, emoji FROM grr_roles WHERE guild_id = ? AND group_name = ?",
                (ctx.guild.id, name))
            lines = []
            for role_id, emoji in await cursor2.fetchall():
                r = ctx.guild.get_role(role_id)
                lines.append(f"{emoji} {r.mention if r else f'<@&{role_id}>'}")
            embed.add_field(name=f"{name} (Max: {max_r})", value="\n".join(lines) or "No roles", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="grredit")
    @has_spower()
    async def grredit(self, ctx):
        cursor = await db.db.execute(
            "SELECT group_name FROM group_reaction_roles WHERE guild_id = ?",
            (ctx.guild.id,))
        groups = [r[0] for r in await cursor.fetchall()]
        if not groups:
            return await ctx.send(embed=info_embed("No groups found."))
        lines = [f"{i+1}. {name}" for i, name in enumerate(groups)]
        embed = info_embed("Edit Group Reaction Roles", "\n".join(lines))
        await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            idx = int(reply.content.strip()) - 1
            if 0 <= idx < len(groups):
                name = groups[idx]
                cursor2 = await db.db.execute(
                    "SELECT role_id, emoji FROM grr_roles WHERE guild_id = ? AND group_name = ?",
                    (ctx.guild.id, name))
                roles = [r for r in await cursor2.fetchall()]
                lines = [f"{i+1}. {emoji} {ctx.guild.get_role(rid).mention if ctx.guild.get_role(rid) else f'<@&{rid}>'}" for i, (rid, emoji) in enumerate(roles)]
                embed2 = info_embed(f"Editing: {name}", "\n".join(lines))
                embed2.set_footer(text="Type **delete** to delete group, number to remove role, or @role to add.")
                await ctx.send(embed=embed2)
        except:
            pass


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))

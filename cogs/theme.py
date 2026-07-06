import discord
from discord.ext import commands
import json
from utils.database import db
from utils.checks import is_owner_or_dev
from utils.embeds import *
from cogs.owner import ConfirmView


class Theme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="theme")
    @is_owner_or_dev()
    async def theme(self, ctx):
        active_theme = await db.get_active_theme()
        all_themes = await db.get_all_themes()
        active_name = active_theme["name"] if active_theme else "None"
        lines = []
        for t in all_themes:
            check = "✅" if t["is_active"] else ""
            prefixes = json.loads(t["prefixes"]) if t["prefixes"] else ["meow"]
            lines.append(f"{t['name']} {check}\n   Prefix: {', '.join(prefixes)}\n   Currency: {t['currency_name'] or 'None'} {t['currency_emoji'] or ''}")
        embed = info_embed("Theme Management",
            f"Current theme: ✅ {active_name}\n\n" + "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)))
        await ctx.send(embed=embed)

        reply = await self._wait_for_reply(ctx)
        if reply:
            all_themes_list = [t["name"] for t in all_themes]
            if reply.strip().isdigit():
                idx = int(reply.strip()) - 1
                if 0 <= idx < len(all_themes_list):
                    await db.set_active_theme(all_themes_list[idx])
                    await ctx.send(embed=success_embed(f"Theme changed to {all_themes_list[idx]}!"))

    @commands.command(name="createtheme")
    @is_owner_or_dev()
    async def create_theme(self, ctx):
        await ctx.send("Theme name?")
        try:
            name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            await ctx.send(f"Prefix for {name}?")
            prefix = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            await db.create_theme(name, [prefix])
            await ctx.send(embed=info_embed(f"Prefix added", f"Successfully added {prefix} in {name}"))
            await ctx.send("Global Currency name for this theme?")
            cur_name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            await ctx.send("Emoji for currency? (type :emoji:)")
            emoji = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            await db.create_theme(name, [prefix], cur_name, emoji)
            embed = info_embed("Theme created!",
                f"**{name}**\nPrefix: {prefix}\nCurrency: {cur_name} {emoji}")
            await ctx.send(embed=embed)
        except:
            await ctx.send(embed=error_embed("Timed out."))

    @commands.command(name="deletetheme")
    @is_owner_or_dev()
    async def delete_theme(self, ctx):
        await ctx.send("Theme name to delete?")
        try:
            name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
            view = ConfirmView(ctx, f"Delete theme '{name}'?")
            msg = await ctx.send(embed=warning_embed("Delete Theme", f"Delete theme '{name}'?"), view=view)
            await view.wait()
            if view.value:
                await db.delete_theme(name)
                await msg.edit(embed=success_embed(f"Deleted {name}"), view=None)
        except:
            pass

    @commands.command(name="changetheme")
    @is_owner_or_dev()
    async def change_theme(self, ctx):
        all_themes = await db.get_all_themes()
        lines = [f"{i+1}. {t['name']}" for i, t in enumerate(all_themes)]
        await ctx.send(embed=info_embed("Select theme:", "\n".join(lines)))
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            idx = int(reply.strip()) - 1
            if 0 <= idx < len(all_themes):
                await db.set_active_theme(all_themes[idx]["name"])
                await ctx.send(embed=success_embed(f"Theme changed to {all_themes[idx]['name']}!"))
        except:
            pass

    async def _wait_for_reply(self, ctx):
        try:
            return await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
        except:
            return None


async def setup(bot):
    await bot.add_cog(Theme(bot))

import discord
from discord.ext import commands
import json
import random
import asyncio
from utils.database import db
from utils.checks import is_owner_or_dev, has_any_power
from utils.embeds import *


class PlayGIF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands = {}
        self._tasks_started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._tasks_started:
            self._tasks_started = True
            asyncio.create_task(self.load_commands())

    async def load_commands(self):
        await self.bot.wait_until_ready()
        cursor = await db.db.execute("SELECT name, data FROM play_gif_commands")
        self.commands = {}
        for row in await cursor.fetchall():
            self.commands[row[0]] = json.loads(row[1])

    async def save_command(self, name, data):
        await db.db.execute(
            "INSERT OR REPLACE INTO play_gif_commands (name, data) VALUES (?, ?)",
            (name, json.dumps(data)))
        await db.db.commit()
        self.commands[name] = data

    @commands.command(name="gifplaysetup")
    @is_owner_or_dev()
    async def gifplaysetup(self, ctx):
        embed = info_embed("Play GIF Setup",
            "Current play commands:\n" +
            "\n".join(f"- meow {name} [target]" for name in self.commands.keys()) +
            "\n\nType number to edit, **create** for new, or **done**.")
        msg = await ctx.send(embed=embed)
        try:
            reply = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            if reply.content.strip().lower() == "create":
                await ctx.send("Prefix play command?\nFormat: meow [command] [target]")
                cmd_name = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                cmd_name = cmd_name.replace("meow ", "").split()[0]
                await ctx.send("Message for this command?\nUse [user] and [target].")
                msg_text = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await ctx.send("GIF URL?")
                gif = (await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)).content.strip()
                await self.save_command(cmd_name, {"cases": [{"message": msg_text, "gif": gif}]})
                await ctx.send(embed=success_embed(f"Created meow {cmd_name}!"))
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        content = message.content.lower().strip()
        prefixes = await db.get_prefixes()
        all_prefixes = ["meow"] + list(prefixes)
        for p in all_prefixes:
            if content.startswith(p.lower() + " "):
                args = content[len(p):].strip().split()
                if len(args) >= 2 and args[0] == "play":
                    args = args[1:]  # remove 'play'
                if len(args) >= 2:
                    cmd = args[0]
                    target_str = args[1]
                    if cmd in self.commands:
                        data = self.commands[cmd]
                        cases = data.get("cases", [])
                        if cases:
                            case = random.choice(cases)
                            target = message.mentions[0] if message.mentions else None
                            target_name = target.mention if target else target_str
                            msg_text = case["message"].replace("[user]", message.author.mention).replace("[target]", target_name)
                            embed = info_embed("", msg_text)
                            gif = case.get("gif", "")
                            if gif and gif.startswith("http"):
                                embed.set_image(url=gif)
                            await message.channel.send(embed=embed)
                        break

    async def play_help(self, ctx):
        lines = [f"• meow {name} [target]" for name in self.commands.keys()]
        embed = info_embed("Play GIF Commands", "\n".join(lines) or "No commands configured.", private=True)
        await ctx.send(embed=embed)

    @commands.command(name="meowon")
    @has_any_power()
    async def meow_on(self, ctx, target: str = None):
        if target == "all":
            await db.set_guild_config(ctx.guild.id, "meow_enabled_all", True)
            await ctx.send(embed=success_embed("Meow prefix enabled for ALL in this channel."))
        elif target == "members":
            await db.set_guild_config(ctx.guild.id, "meow_enabled_members", True)
            await ctx.send(embed=success_embed("Meow prefix enabled for members."))
        elif target == "gif":
            await db.set_guild_config(ctx.guild.id, "gif_enabled", True)
            await ctx.send(embed=success_embed("Play GIF enabled."))

    @commands.command(name="meowoff")
    @has_any_power()
    async def meow_off(self, ctx, target: str = None):
        if target == "all":
            await db.set_guild_config(ctx.guild.id, "meow_enabled_all", False)
            await ctx.send(embed=error_embed("Meow prefix disabled for ALL."))
        elif target == "members":
            await db.set_guild_config(ctx.guild.id, "meow_enabled_members", False)
            await ctx.send(embed=error_embed("Meow prefix disabled for members."))
        elif target == "gif":
            await db.set_guild_config(ctx.guild.id, "gif_enabled", False)
            await ctx.send(embed=error_embed("Play GIF disabled."))


async def setup(bot):
    await bot.add_cog(PlayGIF(bot))

import discord
from discord.ext import commands
from utils.database import db
from utils.embeds import *


class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # Let regular commands handle

        content = message.content.lower().strip()
        prefixes = await db.get_prefixes()
        all_prefixes = ["meow"] + list(prefixes)

        used_prefix = None
        for p in all_prefixes:
            if content.startswith(p.lower() + " "):
                used_prefix = p
                break
            if content == p.lower():
                used_prefix = p
                break

        if not used_prefix:
            return

        args = content[len(used_prefix):].strip().split()
        if not args:
            return

        cmd = args[0]
        rest = " ".join(args[1:])

        if cmd == "use":
            await self.handle_use(ctx, rest)
        elif cmd == "inv":
            cards_cog = self.bot.get_cog("Cards")
            if cards_cog:
                await cards_cog.inv(ctx)
        elif cmd == "wallet":
            wallet_cog = self.bot.get_cog("Wallet")
            if wallet_cog:
                await wallet_cog.wallet(ctx)
        elif cmd == "give":
            await self.handle_give(ctx, rest)
        elif cmd == "shop":
            shop_cog = self.bot.get_cog("Shop")
            if shop_cog:
                await shop_cog.shop(ctx)
        elif cmd == "help":
            embed = info_embed(f"{used_prefix.title()} Commands",
                f"• `{used_prefix} use` — Use items\n"
                f"• `{used_prefix} inv` — View inventory\n"
                f"• `{used_prefix} wallet` — View wallet\n"
                f"• `{used_prefix} give [currency] @user` — Transfer currency\n"
                f"• `{used_prefix} shop` — Browse shop\n"
                f"• `{used_prefix} play help` — List play GIF commands\n"
                f"• `{used_prefix} help` — This menu", private=True)
            await ctx.send(embed=embed)
        elif cmd == "play" and len(args) > 1 and args[1] == "help":
            gif_cog = self.bot.get_cog("PlayGIF")
            if gif_cog:
                await gif_cog.play_help(ctx)

    async def handle_use(self, ctx, rest):
        cards_cog = self.bot.get_cog("Cards")
        if not cards_cog:
            return
        if rest:
            await cards_cog.use_item(ctx, rest.strip().title())
        else:
            await cards_cog.use(ctx)

    async def handle_give(self, ctx, rest):
        parts = rest.split()
        if len(parts) < 2:
            return
        currency = parts[0].title()
        target_str = parts[1]
        if target_str.startswith("<@"):
            uid = int(target_str.strip("<@!>"))
            target = ctx.guild.get_member(uid)
            if not target:
                return
            wallet_cog = self.bot.get_cog("Wallet")
            if wallet_cog:
                await ctx.send("Amount?")
                try:
                    amount_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                    amount = float(amount_msg.content.strip())
                    await wallet_cog.pay(ctx, target, amount, currency)
                except:
                    pass


async def setup(bot):
    await bot.add_cog(Prefix(bot))

import discord
from discord.ext import commands
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from config import TOKEN
from utils.database import db


async def get_prefix(bot, message):
    if message.guild is None:
        return commands.when_mentioned_or("I?")(bot, message)
    if message.content.startswith("I?"):
        return "I?"
    theme_prefixes = await db.get_prefixes()
    all_prefixes = ["I?", "meow"] + list(theme_prefixes)
    return commands.when_mentioned_or(*all_prefixes)(bot, message)


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.owner_id = (await bot.application_info()).owner.id
    owner = await bot.fetch_user(bot.owner_id)
    try:
        await owner.send("hi")
        print(f"Sent 'hi' to owner: {owner}")
    except Exception as e:
        print(f"Could not DM owner: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Error in {event}: {args} {kwargs}")
    import traceback
    traceback.print_exc()


async def load_cogs():
    cogs_list = [
        "cogs.owner", "cogs.jail", "cogs.punishments", "cogs.economy",
        "cogs.shop", "cogs.gifts", "cogs.wallet", "cogs.iconroles",
        "cogs.reactionroles", "cogs.theme", "cogs.prefix", "cogs.playgif",
        "cogs.admin", "cogs.cards", "cogs.events"
    ]
    for cog in cogs_list:
        try:
            await bot.load_extension(cog)
            print(f"Loaded {cog}")
        except Exception as e:
            print(f"Failed to load {cog}: {e}")


async def setup():
    await db.connect()
    await load_cogs()
    print("Setup complete. Starting bot...")


if __name__ == "__main__":
    asyncio.run(setup())
    bot.run(TOKEN, reconnect=True)

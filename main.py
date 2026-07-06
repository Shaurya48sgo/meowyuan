import discord
import os

TOKEN = os.environ["MEOW_YUAN_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    app_info = await bot.application_info()
    owner = app_info.owner
    await owner.send("hi")
    print(f"Sent 'hi' to owner: {owner}")
    await bot.close()

bot.run(TOKEN)

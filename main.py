import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Bot aktif sebagai {bot.user}")

# ================= LOAD COGS =================
async def load_extensions():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.load_extension(f"cogs.{file[:-3]}")
    print("Cogs loaded")

# ================= START =================
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
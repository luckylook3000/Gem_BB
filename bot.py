import os
import discord
import random
import time
import asyncio
import json
import math
import re
import requests
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from quart import Quart, request, jsonify
from multiprocessing import Process

# ==========================================
# 1. CONFIG & SECRETS
# ==========================================
load_dotenv()
TOKEN = os.getenv("DISCORDBOTTOKEN") # Specifically using your Secret name

Config = {
    "Bot Name": "Gem Bet",
    "Bot Icon": "https://cdn.discordapp.com/icons/1314565811410829332/a_f59d3588d80ec8f0ab041a65d6c5a761.gif?size=1024",
    "Towers": {"WinChance": 45, "Multis": [1.42, 2.02, 2.86, 4.05, 5.69]},
    "Mines": {"House": 0.25},
    "Logs": 1314565812950007837,
    "Coinflip": {"1v1": "1314565812950007831", "House": 5},
    "Rains": {"Channel": "1314565812950007834"},
    "Status": {"Message": "Online"},
    "AdminCommands": {
        "UserID": ["1177041430502461523", "1216488230245892186", "1278257618758139905", "1144624389556551750", "1124671288527560844", "1085730642928607272", "1310620656865378355"],
        "OwnerID": ["1177041430502461523"],
    },
    "AutoDeposits": {"Webhook": "https://discord.com/api/webhooks/132161456503285325/QMCu_Mm0bEAgxbnaYEvIM0nnI4jvv7O88uTTn-LFz_ySN3YzTXAMTnFwN85_A"},
    "Withdraws": {"Webhook": "https://discord.com/api/webhooks/1321614565557141608/AyTZcbIPYY2ys2uxx75KT_HYM2MZvzO0w-AM1kuTRU1qGa1l0fs8XwhP7ZQaM"},
    "Affiliates": {"Webhook": "https://discord.com/api/webhooks/1321614563569045596/2w9FsfpUnAb28BxgUP0y1 tequila_s la-C"},
    "Tips": {"Webhook": "https://discord.com/api/webhooks/13216145638702/DwlmXUmA7nwfK-IfdyHmsW86GCsQtCzTpp5jitY9Zhen9Q4hmOmsL"},
    "Promocodes": {"Webhook": "https://discord.com/api/webhooks/1321614562520207431/McdDfjVImju1YWovQIDeHma_AbSJrvscE2vn1kUKEPRJGMHT64_yKTTBAbiARt", "RoleID": "1314565811410829334"},
    "Upgrader": {"House": 0.9},
    "Rakeback": 1,
    "Username": "Gem Bet Bot",
}

# ==========================================
# 2. DATABASE & SAFETY ENGINE
# ==========================================
def init_db():
    files = {
        "data.json": {"users": {}},
        "withdraws.json": [],
        "promocodes.json": [],
        "history.json": {},
        "admins.json": {},
        "deposits.json": []
    }
    for filename, default in files.items():
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                json.dump(default, f, indent=4)

def readdata():
    with open("data.json", "r") as f: return json.load(f)
def writedata(data):
    with open("data.json", "w") as f: json.dump(data, f, indent=4)

def register_user(uid):
    data = readdata()
    if uid not in data['users']:
        data["users"][uid] = {
            "Gems": 1000, "CrashJoinAmount": 100000000, "Rakeback": 0, "Affiliate": None,
            "Affiliate Earnings": 0, "Deposited": 0, "Withdrawn": 0, "Wagered": 0,
            "Tips Got": 0, "Tips Sent": 0, "Total Rained": 0, "Rain Earnings": 0,
            "Net Profit": 0, "linkedusername": None
        }
        writedata(data)

def get_gems(uid):
    data = readdata()
    return data['users'].get(uid, {}).get("Gems", 1000)

def add_gems(uid, amount):
    data = readdata()
    if uid not in data['users']: register_user(uid)
    data['users'][uid]['Gems'] += amount
    writedata(data)

def subtract_gems(uid, amount):
    data = readdata()
    if uid in data['users']:
        data['users'][uid]['Gems'] -= amount
        writedata(data)

def add_suffix(val):
    val = abs(val)
    if val >= 1e15: return f"{val/1e15:.1f}Q"
    if val >= 1e12: return f"{val/1e12:.1f}T"
    if val >= 1e9: return f"{val/1e9:.1f}B"
    if val >= 1e6: return f"{val/1e6:.1f}M"
    if val >= 1e3: return f"{val/1e3:.1f}K"
    return str(val)

def suffix_to_int(s):
    s = s.lower()
    suffixes = {'k': 1e3, 'm': 1e6, 'b': 1e9, 't': 1e12, 'q': 1e15}
    if s[-1] in suffixes: return int(float(s[:-1]) * suffixes[s[-1]])
    return int(s)

# ==========================================
# 3. GAME LOCKING & COOLDOWNS
# ==========================================
active_games = {} # Tracks {user_id: True}
game_cooldowns = {} # Tracks {user_id: timestamp}

async def can_play(user_id):
    now = time.time()
    if user_id in active_games:
        return False, "You already have a game in progress! Finish that one first. ⏳"
    if user_id in game_cooldowns and (now - game_cooldowns[user_id]) < 1.0:
        return False, "Slow down! Please wait 1 second between games. ⏱️"
    return True, None

# ==========================================
# 4. BOT CORE & SLASH COMMANDS
# ==========================================
class GemBetBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Global Slash Commands Synced!")

bot = GemBetBot()

# --- Utility Functions ---
def get_casino_embed(title, desc, color=0x3471eb):
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_footer(text="GemBet💎 | Virtual Games", icon_url=Config["Bot Icon"])
    return embed

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("🚀 **Commands forced to sync! Restart Discord (Ctrl+R).**")

# --- ECONOMY COMMANDS ---
@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    uid = str((user or interaction.user).id)
    register_user(uid)
    bal = get_gems(uid)
    await interaction.response.send_message(embed=get_casino_embed("💰 Balance", f"{user or interaction.user} has **{add_suffix(bal)}** gems.", 0x00ff00))

@bot.tree.command(name="tip", description="Tip a user")
async def tip(interaction: discord.Interaction, member: discord.Member, amount: str):
    uid = str(interaction.user.id)
    target_id = str(member.id)
    amt = suffix_to_int(amount)
    
    if get_gems(uid) < amt: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)
    
    subtract_gems(uid, amt)
    add_gems(target_id, amt)
    await interaction.response.send_message(embed=get_casino_embed("💸 Tip Sent", f"{interaction.user.mention} tipped {member.mention} **{add_suffix(amt)}** gems!", 0xf1c40f))

# --- GAMES (Interactive & Locked) ---

@bot.tree.command(name="dice", description="Roll dice against the bot")
async def dice(interaction: discord.Interaction, bet: str):
    uid = str(interaction.user.id)
    # Lock & Cooldown Check
    can, msg = await can_play(uid)
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    bet_int = suffix_to_int(bet)
    if get_gems(uid) < bet_int: return await interaction.response.send_message("❌ Not enough gems!", ephemeral=True)

    active_games[uid] = True
    subtract_gems(uid, bet_int)
    
    await interaction.response.send_message(embed=get_casino_embed("🎲 Dice Roll", "Rolling... 🎰"))
    
    # Animation
    for _ in range(3):
        await asyncio.sleep(0.6)
        await interaction.edit_original_response(embed=get_casino_embed("🎲 Dice Roll", f"Rolling... {random.randint(1,6)}"))
    
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    if user_roll > bot_roll:
        winnings = int(bet_int * 1.98)
        add_gems(uid, winnings)
        res = f"🎉 **YOU WIN!**\nYour Roll: {user_roll} | Bot: {bot_roll}\nWon: **{add_suffix(winnings)}**"
        col = 0x00ff00
    elif user_roll < bot_roll:
        res = f"💀 **YOU LOST!**\nYour Roll: {user_roll} | Bot: {bot_roll}\nLost: **{add_suffix(bet_int)}**"
        col = 0xff0000
    else:
        add_gems(uid, bet_int)
        res = f"🤝 **TIE!**\nBoth rolled {user_roll}. Bet returned."
        col = 0xffff00

    await interaction.edit_original_response(embed=get_casino_embed("🎲 Dice Result", res, col))
    
    # Unlock and set cooldown
    del active_games[uid]
    game_cooldowns[uid] = time.time()

@bot.tree.command(name="blackjack", description="Play Blackjack!")
async def blackjack(interaction: discord.Interaction, bet: str):
    uid = str(interaction.user.id)
    can, msg = await can_play(uid)
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    bet_int = suffix_to_int(bet)
    if get_gems(uid) < bet_int: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)
    
    active_games[uid] = True
    subtract_gems(uid, bet_int)

    # Basic BJ Logic
    player = [random.randint(2, 11), random.randint(2, 11)]
    dealer = [random.randint(2, 11), random.randint(2, 11)]

    class BJView(discord.ui.View):
        def __init__(self, user, bet, p, d):
            super().__init__(timeout=60)
            self.user, self.bet, self.p, self.d = user, bet, p, d

        @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
        async def hit(self, inter, btn):
            if inter.user.id != self.user: return await inter.response.defer()
            self.p.append(random.randint(2, 11))
            if sum(self.p) > 21:
                await inter.response.edit_message(content=f"💥 **BUST!** {sum(self.p)}. Lost {add_suffix(self.bet)} gems.", embed=None, view=None)
                active_games.pop(str(self.user.id), None)
                game_cooldowns[str(self.user.id)] = time.time()
            else:
                await inter.response.edit_message(content=f"🃏 Hand: `{self.p}` (Total: {sum(self.p)})", view=self)

        @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
        async def stand(self, inter, btn):
            if inter.user.id != self.user: return await inter.response.defer()
            while sum(self.d) < 17: self.d.append(random.randint(2, 11))
            p_sum, d_sum = sum(self.p), sum(self.d)
            if d_sum > 21 or p_sum > d_sum:
                add_gems(str(self.user.id), self.bet * 2)
                res = "🎉 **WIN!**"
            elif p_sum < d_sum:
                res = "💀 **LOSS!**"
            else:
                add_gems(str(self.user.id), self.bet)
                res = "🤝 **TIE!**"
            await inter.response.edit_message(content=f"{res}\nPlayer: {p_sum} | Dealer: {d_sum}", embed=None, view=None)
            active_games.pop(str(self.user.id), None)
            game_cooldowns[str(self.user.id)] = time.time()

    await interaction.response.send_message(f"🃏 **Blackjack!** Your hand: `{player}` (Total: {sum(player)})\nDealer shows: `{dealer[0]}`", view=BJView(interaction.user.id, bet_int, player, dealer))

# ==========================================
# 5. WEB SERVER (QUART)
# ==========================================
app = Quart(__name__)

@app.route('/webhook', methods=['POST'])
async def handle_webhook():
    return jsonify({"status": "ok"}), 200

def run_server():
    app.run(host="0.0.0.0", port=1161)

# ==========================================
# 6. EXECUTION
# ==========================================
if __name__ == '__main__':
    init_db()
    # Start server in separate process
    p = Process(target=run_server)
    p.start()
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        p.terminate()

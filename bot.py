import os
import sys
import subprocess

# ==========================================
# 🚨 SELF-INSTALLER (Saves you from Build Errors)
# ==========================================
def install_dependencies():
    try:
        import discord
        import dotenv
    except ImportError:
        print("📦 Installing missing libraries... please wait...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "discord.py", "python-dotenv"])
        print("✅ Libraries installed! Restarting bot...")
        os.execv(sys.executable, ['python'] + sys.argv)

install_dependencies()

# Now we import the rest
import discord
import random
import asyncio
import json
import time
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

# ==========================================
# 1. CONFIG & SECRETS
# ==========================================
load_dotenv()
# Try both common secret names just in case
TOKEN = os.getenv("DISCORDBOTTOKEN") or os.getenv("TOKEN")

if not TOKEN:
    print("❌ ERROR: No Token found in Secrets! Please add DISCORDBOTTOKEN to your lock icon 🔒")
    sys.exit()

# ==========================================
# 2. DATABASE ENGINE (Auto-Creates everything)
# ==========================================
DATA_FILE = "data.json"

def init_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}}, f, indent=4)

def load_bal():
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}}

def save_bal(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

def get_bal(u_id):
    data = load_bal()
    return data['users'].get(str(u_id), 1000)

def update_bal(u_id, amt):
    data = load_bal()
    u_id = str(u_id)
    if u_id not in data['users']:
        data['users'][u_id] = {"Gems": 1000}
    data['users'][u_id]['Gems'] += amt
    save_bal(data)
    return data['users'][u_id]['Gems']

def add_suffix(val):
    val = abs(val)
    if val >= 1e12: return f"{val/1e12:.1f}T"
    if val >= 1e9: return f"{val/1e9:.1f}B"
    if val >= 1e6: return f"{val/1e6:.1f}M"
    if val >= 1e3: return f"{val/1e3:.1f}K"
    return str(val)

def suffix_to_int(s):
    s = s.lower()
    suffixes = {'k': 1e3, 'm': 1e6, 'b': 1e9, 't': 1e12}
    if s[-1] in suffixes: return int(float(s[:-1]) * suffixes[s[-1]])
    return int(s)

# ==========================================
# 3. GAME LOCKS
# ==========================================
active_games = {} 
game_cooldowns = {}

async def can_play(user_id):
    now = time.time()
    if user_id in active_games:
        return False, "You already have a game in progress! ⏳"
    if user_id in game_cooldowns and (now - game_cooldowns[user_id]) < 1.0:
        return False, "Slow down! 1 second cooldown. ⏱️"
    return True, None

# ==========================================
# 4. BOT CORE
# ==========================================
class GemBetBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = GemBetBot()

def get_embed(title, desc, color=0x3471eb):
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_footer(text="GemBet💎 | Virtual Games")
    return embed

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("🚀 **Synced! Restart Discord (Ctrl+R) and type `/`**")

@bot.tree.command(name="balance", description="Check gems")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    uid = str((user or interaction.user).id)
    await interaction.response.send_message(embed=get_embed("💰 Balance", f"{user or interaction.user} has **{add_suffix(get_bal(uid))}** gems.", 0x00ff00))

@bot.tree.command(name="dice", description="Bet on high or low")
@app_commands.choices(choice=[app_commands.Choice(name="High", value="high"), app_commands.Choice(name="Low", value="low")])
async def dice(interaction: discord.Interaction, bet: str, choice: str):
    uid = str(interaction.user.id)
    can, msg = await can_play(uid)
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    amt = suffix_to_int(bet)
    if get_bal(uid) < amt: return await interaction.response.send_message("❌ Not enough gems!", ephemeral=True)

    active_games[uid] = True
    update_bal(uid, -amt)
    await interaction.response.send_message(embed=get_embed("🎲 Dice", f"Spinning... 🎰"))
    
    await asyncio.sleep(1)
    roll = random.randint(1, 6)
    win = (choice == 'high' and roll >= 4) or (choice == 'low' and roll <= 3)
    
    if win:
        update_bal(uid, amt * 2)
        res, col = f"🎉 **WIN!** Rolled {roll}. Won **{add_suffix(amt*2)}** gems!", 0x00ff00
    else:
        res, col = f"💀 **LOSS!** Rolled {roll}. Lost **{add_suffix(amt)}** gems!", 0xff0000
    
    await interaction.edit_original_response(embed=get_embed("🎲 Result", f"{res}\nBalance: **{add_suffix(get_bal(uid))}**", col))
    del active_games[uid]
    game_cooldowns[uid] = time.time()

@bot.event
async def on_ready():
    init_db()
    print(f'👑 Gem Bet is ONLINE as {bot.user}')

bot.run(TOKEN)


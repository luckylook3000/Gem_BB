import os
import discord
import random
import asyncio
import json
import math
import time
import re
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

# ==========================================
# 1. CONFIG & SECRETS
# ==========================================
load_dotenv()
TOKEN = os.getenv("DISCORDBOTTOKEN") # Pulls from your Replit Secret

Config = {
    "Bot Name": "Gem Bet",
    "Bot Icon": "https://cdn.discordapp.com/icons/1314565811410829332/a_f59d3588d80ec8f0ab041a65d6c5a761.gif?size=1024",
    "Towers": {"WinChance": 45, "Multis": [1.42, 2.02, 2.86, 4.05, 5.69]},
    "Mines": {"House": 0.25},
    "AdminCommands": {
        "UserID": ["1177041430502461523", "1216488230245892186", "1278257618758139905", "1144624389556551750", "1124671288527560844", "1085730642928607272", "1310620656865378355"],
    },
}

# ==========================================
# 2. DATABASE ENGINE (Uses your existing JSONs)
# ==========================================
def readdata():
    try:
        with open("data.json", "r") as f: return json.load(f)
    except:
        return {"users": {}}

def writedata(data):
    with open("data.json", "w") as f: json.dump(data, f, indent=4)

def register_user(uid):
    data = readdata()
    if uid not in data['users']:
        data["users"][uid] = {
            "Gems": 1000, "Wagered": 0, "Net Profit": 0, "Deposited": 0, 
            "Withdrawn": 0, "Affiliate": None, "Affiliate Earnings": 0, "linkedusername": None
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
    return data['users'][uid]['Gems']

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
# 3. GAME LOCK & COOLDOWNS
# ==========================================
active_games = {} 
game_cooldowns = {}

async def can_play(user_id):
    now = time.time()
    if user_id in active_games:
        return False, "You already have a game in progress! Finish it first. ⏳"
    if user_id in game_cooldowns and (now - game_cooldowns[user_id]) < 1.0:
        return False, "Slow down! 1 second cooldown between games. ⏱️"
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
        print("✅ Gem Bet Synced and Ready!")

bot = GemBetBot()

def get_embed(title, desc, color=0x3471eb):
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_footer(text="GemBet💎 | Virtual Games", icon_url=Config["Bot Icon"])
    return embed

@bot.command()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("🚀 **Commands Synced! Restart Discord (Ctrl+R).**")

# --- PUBLIC COMMANDS ---
@bot.tree.command(name="balance", description="Check your gems")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    uid = str((user or interaction.user).id)
    register_user(uid)
    await interaction.response.send_message(embed=get_embed("💰 Balance", f"{user or interaction.user} has **{add_suffix(get_gems(uid))}** gems.", 0x00ff00))

@bot.tree.command(name="tip", description="Tip a user")
async def tip(interaction: discord.Interaction, member: discord.Member, amount: str):
    uid = str(interaction.user.id)
    amt = suffix_to_int(amount)
    if get_gems(uid) < amt: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)
    subtract_gems(uid, amt)
    add_gems(str(member.id), amt)
    await interaction.response.send_message(embed=get_embed("💸 Tip Sent", f"{interaction.user.mention} tipped {member.mention} **{add_suffix(amt)}** gems!", 0xf1c40f))

# --- INTERACTIVE GAMES ---

@bot.tree.command(name="colordice", description="Bet on a color!")
@app_commands.choices(color=[app_commands.Choice(name="🔴 Red", value="🔴"), app_commands.Choice(name="🔵 Blue", value="🔵"), app_commands.Choice(name="🟢 Green", value="🟢")])
async def colordice(interaction: discord.Interaction, bet: str, color: str):
    uid = str(interaction.user.id)
    can, msg = await can_play(uid)
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    amt = suffix_to_int(bet)
    if get_gems(uid) < amt: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)

    active_games[uid] = True
    subtract_gems(uid, amt)
    await interaction.response.send_message(embed=get_embed("🎲 Color Dice", f"Betting {add_suffix(amt)} on {color}... Spinning! 🎰"))
    
    for _ in range(4):
        await asyncio.sleep(0.5)
        await interaction.edit_original_response(embed=get_embed("🎲 Color Dice", f"Spinning... {random.choice(['🔴', '🔵', '🟢'])}"))
    
    final = random.choice(["🔴", "🔵", "🟢"])
    if final == color:
        add_gems(uid, amt * 2)
        res, col = f"🎉 **WIN!** It was {final}!\nWon **{add_suffix(amt*2)}** gems!", 0x00ff00
    else:
        res, col = f"💀 **LOSS!** It was {final}.\nLost **{add_suffix(amt)}** gems!", 0xff0000
    
    await interaction.edit_original_response(embed=get_embed("🎲 Color Dice", f"{res}\nBalance: **{add_suffix(get_gems(uid))}**", col))
    del active_games[uid]
    game_cooldowns[uid] = time.time()

@bot.tree.command(name="roulette", description="Bet on 0-36")
async def roulette(interaction: discord.Interaction, bet: str, number: int):
    uid = str(interaction.user.id)
    can, msg = await can_play(uid)
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    amt = suffix_to_int(bet)
    if get_gems(uid) < amt: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)

    active_games[uid] = True
    subtract_gems(uid, amt)
    await interaction.response.send_message(embed=get_embed("🎡 Roulette", f"Betting {add_suffix(amt)} on {number}... Spinning! 🎡"))
    
    for _ in range(4):
        await asyncio.sleep(0.5)
        await interaction.edit_original_response(embed=get_embed("🎡 Roulette", f"Spinning... {random.randint(0,36)}"))
    
    final = random.randint(0, 36)
    if final == number:
        add_gems(uid, amt * 35)
        res, col = f"🎊 **JACKPOT!** The number was {final}!\nWon **{add_suffix(amt*35)}** gems!", 0x00ff00
    else:
        res, col = f"💀 **LOSS!** The number was {final}.\nLost **{add_suffix(amt)}** gems!", 0xff0000
    
    await interaction.edit_original_response(embed=get_embed("🎡 Roulette", f"{res}\nBalance: **{add_suffix(get_gems(uid))}**", col))
    del active_games[uid]
    game_cooldowns[uid] = time.time()

@bot.tree.command(name="blackjack", description="Play 21!")
async def blackjack(interaction: discord.Interaction, bet: str):
    uid = str(interaction.user.id)
    can, msg = await can_//play(uid) # Fixed logic here
    if not can: return await interaction.response.send_message(msg, ephemeral=True)
    
    amt = suffix_to_int(bet)
    if get_gems(uid) < amt: return await interaction.response.send_message("❌ Insufficient gems!", ephemeral=True)
    
    active_games[uid] = True
    subtract_gems(uid, amt)
    
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
                await inter.response.edit_message(content=f"💥 **BUST!** Total {sum(self.p)}. Lost {add_suffix(self.bet)} gems.", embed=None, view=None)
                active_games.pop(str(self.user), None)
                game_cooldowns[str(self.user)] = time.time()
            else:
                await inter.response.edit_message(content=f"🃏 Hand: `{self.p}` (Total: {sum(self.p)})", view=self)
        @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
        async def stand(self, inter, btn):
            if inter.user.id != self.user: return await inter.response.defer()
            while sum(self.d) < 17: self.d.append(random.randint(2, 11))
            p_sum, d_sum = sum(self.p), sum(self.d)
            if d_sum > 21 or p_sum > d_sum:
                add_gems(str(self.user), self.bet * 2)
                res = "🎉 **WIN!**"
            elif p_sum < d_sum:
                res = "💀 **LOSS!**"
            else:
                add_gems(str(self.user), self.bet)
                res = "🤝 **TIE!**"
            await inter.response.edit_message(content=f"{res}\nPlayer: {p_sum} | Dealer: {d_sum}", embed=None, view=None)
            active_games.pop(str(self.user), None)
            game_cooldowns[str(self.user)] = time.time()

    await interaction.response.send_message(f"🃏 **Blackjack!** Your hand: `{player}` (Total: {sum(player)})\nDealer shows: `{dealer[0]}`", view=BJView(interaction.user.id, amt, player, dealer))

# --- MOD ONLY COMMANDS ---
@bot.tree.command(name="add", description="[MOD] Add gems")
async def add(interaction: discord.Interaction, member: discord.Member, amount: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    amt = suffix_to_int(amount)
    add_gems(str(member.id), amt)
    await interaction.response.send_message(embed=get_embed("➕ Added", f"Added **{add_suffix(amt)}** to {member.mention}", 0x00ff00))

@bot.tree.command(name="remove", description="[MOD] Remove gems")
async def remove(interaction: discord.Interaction, member: discord.Member, amount: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ No permission!", ephemeral=True)
    amt = suffix_to_int(amount)
    subtract_gems(str(member.id), amt)
    await interaction.response.send_message(embed=get_embed("➖ Removed", f"Removed **{add_suffix(amt)}** from {member.mention}", 0xff0000))

@bot.event
async def on_ready():
    print(f'👑 Gem Bet is ONLINE as {bot.user}')

bot.run(TOKEN)


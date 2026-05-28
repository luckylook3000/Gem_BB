from datetime import datetime, timedelta, timezone
import string
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from discord.ui import Button, View

import json
import random
import time
import asyncio
import threading
import os
from enum import Enum
import requests
import math
from quart import Quart, request, jsonify
import re
import logging
import aiohttp

from blockcypher import get_transaction_details
from blockcypher import get_address_overview
from blockcypher import subscribe_to_address_webhook

app = Quart(__name__)

Config = {
    "Bot Name": "name here",  # will be in all embeds
    "Bot Icon": "https://cdn.discordapp.com/icons/1314565811410829332/a_f59d3588d80ec8f0ab041a65d6c5a761.gif?size=1024",  # will be in all embeds
    "Towers": {  # Config for towers
        "WinChance": 45,  # Percent they will win when they click a tower
        "Multis": [1.42, 2.02, 2.86, 4.05, 5.69]  # Multipliers On The Blocks
    },
    "Mines": {  # Config for mines
        "House": 0.25,  # The Multiplier Will Be Multiplied by 1.00 - This
    },
    "Logs": 1314565812950007837,  # log channel
    "Coinflip": {  # Config for coinflip
        "1v1": "1314565812950007831",  # Channel That Coinflips Be In
        "House": 5  # House Edge (%)
    },
    "Rains": {  # Config for rains
        "Channel": "1314565812950007834",  # Set to the id the channel rains will be in
    },
    "Status": {
        "Message": "Offline",
    },
    "AdminCommands": {
        "UserID": ["1177041430502461523", "1216488230245892186", "1278257618758139905", "1144624389556551750", "1124671288527560844", "1085730642928607272", "1310620656865378355"],
        "OwnerID":
["1177041430502461523"],
    },
    "AutoDeposits": {
        "Webhook": "https://discord.com/api/webhooks/1321614565032853525/QMCu_Mm0bEAgxbnaYEvIM0nnI4jvv7O88uTTn-LFz_ySN3YzTXAMTnFwN85_A",  # auto deposits or /confirmdeposit
    },
    "Withdraws": {
        "Webhook": "https://discord.com/api/webhooks/1321614565557141608/AyTZcbIPYY2ys2uxx75KT_HYM2MZvzO0w-AM1kuTRU1qGa1l0fs8XwhP7ZQaM",
    },
    "Affiliates": {
        "Webhook": "https://discord.com/api/webhooks/1321614563569045596/2w9FsfpUnAb28BxgUP0y16WQENPPUVsd4I6nZw3zGximxfkPyqvhtvyA5EcSERT",  # webhook for when someone gets affiliated
    },
    "Tips": {
        "Webhook": "https://discord.com/api/webhooks/1321614563853702/DwlmXUmA7nwfK-IfdyHmsW86GCsQtCzTpp5jitY9Zhen9QfQ4hmOms-lQHSY",  # webhook for tips
    },
    "Promocodes": {
        "Webhook": "https://discord.com/api/webhooks/1321614562520207431/McdDfjVImju1YWovQIDeHma_AbSJrvscE2vn1kUKEPRJGMHT64_yKTTBAbiARt",  # webhook for promocodes
        "RoleID": "1314565811410829334",  # for ping
    },
    "Upgrader": {  # Config for upgrader
        "House": 0.9  # house edge (winnings*house)
    },
    "Rakeback": 1,  # Rakeback %
    "Username": "nothing here.",  # The Username Of The Account Running The Bot
    "DiscordBotToken": "",  # The token of the discord bot
    "AddGemsWebhook": "https://discord.com/api/webhooks/1321614561866154086/MLXaXAqgT0R030D-",
    "SetGemsWebhook": "https://discord.com/api/webhooks/1321614561866154086/MLXaXAqgT0R030D-"# New private channel webhook for /addgems
}

username = Config['Username']

def multiplier_to_percentage(multiplier, house):
    percentage2 = (100 / multiplier) * house
    return percentage2
def percentage(percent, whole) :
    return (percent * whole) / 100.0

rb = Config['Rakeback']

TowersMultis = [1.0, 1.5, 2, 2.5, 3.0, 3.5]

MineHouseEdge = Config['Mines']['House']


def roll_percentage(percent) :
    random_num = random.uniform(0, 100)
    if random_num <= percent :
        return True
    else :
        return False


def calculate_mines_multiplier(minesamount, diamonds, houseedge) :
    def nCr(n, r) :
        f = math.factorial
        return f(n) // f(r) // f(n - r)

    house_edge = houseedge
    return (1 - house_edge) * nCr(25, diamonds) / nCr(25 - minesamount, diamonds)
def succeed(message):
    return discord.Embed(description=f":gem: {message}", color = 0x3471eb)
def infoe(message):
    return discord.Embed(description=f":information_source: {message}", color = 0x3471eb)
def fail(message):
    return discord.Embed(description=f":x: {message}", color = 0x3471eb)
def generate_board(minesa) :
    board = [
        ["s", "s", "s", "s", "s"],
        ["s", "s", "s", "s", "s"],
        ["s", "s", "s", "s", "s"],
        ["s", "s", "s", "s", "s"],
        ["s", "s", "s", "s", "s"],
    ]
    for index in range(0, minesa) :
        end = False
        while not end :
            row = random.randint(0, 4)
            collum = random.randint(0, 4)
            if board[row][collum] == "s" :
                board[row][collum] = "m"
                end = True
    return board


class CoinSide(Enum) :
    Heads = "Heads"
    Tails = "Tails"
class Colors(Enum):
    Purple = "Purple (2x)"
    Blue = "Blue (2x)"
    Gold = "Gold (5x)"

class RPSSide(Enum) :
    Rock = "Rock"
    Paper = "Paper"
    Scissors = "Scissors"
rpsgames = []
words = ['apple', 'banana', 'fruit', 'up', 'is', 'w', 'a', 'fr', 'shift', 'left', 'down', 'code']
rains = []

def suffix_to_int(s) :
    suffixes = {
        'k' : 3,
        'm' : 6,
        'b' : 9,
        't' : 12,
        'q' : 15
    }

    suffix = s[-1].lower()
    if suffix in suffixes :
        num = float(s[:-1]) * 10 ** suffixes[suffix]
    else :
        num = float(s)

    return int(num)

def readdata():
    with open("data.json", "r") as infile:
        return json.load(infile)

def writedata(data):
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, indent=4)

def get_cases():
    data = readdata()
    return data['cases']

def add_bet(userid, bet, winnings):
    db = readdata()
    db['users'][userid]['Wagered'] += bet
    profit = winnings-bet
    db['users'][userid]['Net Profit'] += profit
    writedata(db)

caseslist = [case['Name'] for case in get_cases()]

def get_affiliate(uid):
    data = readdata()
    return data['users'][uid].get("Affiliate", None)

def get_linkedusername(uid):
    data = readdata()
    return data['users'][uid].get("linkedusername", None)

def set_affiliate(uid, uid2):
    data = readdata()
    data['users'][uid]["Affiliate"] = uid2
    writedata(data)
    
def set_linkedusername(uid, uid2):
    data = readdata()
    data['users'][uid]['linkedusername'] = uid2
    writedata(data)

def send_webhook(embed):
    webhook_url = Config["Affiliates"]["Webhook"]
    data = {"embeds": [embed.to_dict()]}
    requests.post(webhook_url, json=data)
def is_registered(uid):
    data = readdata()
    return uid in data['users']

def register_user(uid):
    if not is_registered(uid):
        data = readdata()
        data["users"][uid] = {
            "Gems": 0,
            "CrashJoinAmount": 100000000,
            "Rakeback": 0,
            "Affiliate": None,
            "Affiliate Earnings": 0,
            "Deposited": 0,
            "Withdrawn": 0,
            "Wagered": 0,
            "Tips Got": 0,
            "Tips Sent": 0,
            "Total Rained": 0,
            "Rain Earnings": 0,
            "Net Profit": 0,
            "linkedusername": None
        }
        writedata(data)

def add_code(item):
    with open("deposits.json", "r") as f:
        codes2 = json.loads(f.read())
    codes2.append(item)
    with open("deposits.json", "w") as f:
        f.write(json.dumps(codes2))

def update_withdrawn_amount(user_id: str, amount: int):
    database = readdata()
    database['users'][user_id]['Withdrawn'] += amount
    writedata(database)

def remove_code(item):
    with open("deposits.json", "r") as f:
        codes2 = json.loads(f.read())
    codes2.remove(item)
    with open("deposits.json", "w") as f:
        f.write(json.dumps(codes2))

def get_codes():
    with open("deposits.json", "r") as f:
        codes2 = json.loads(f.read())
    return codes2

def get_gems(uid):
    try:
        data = readdata()
        return data['users'][uid]['Gems']
    except:
        pass

def set_gems(uid, gems):
    try :
        data = readdata()
        data['users'][uid]['Gems'] = gems
        writedata(data)
    except:
        pass

def get_rain_earn(uid):
    try :
        data = readdata()
        return data['users'][uid]['Rain Earnings']
    except:
        pass

def set_rain_earn(uid, rain_earnings):
    try :
        data = readdata()
        data['users'][uid]['Rain Earnings'] = rain_earnings
        writedata(data)
    except:
        pass

def get_rake_back(uid):
    data = readdata()
    return data['users'][uid].get("Rakeback", 0)

def set_rake_back(uid, amount):
    data = readdata()
    data['users'][uid]['Rakeback'] = amount
    writedata(data)

def add_rake_back(uid, amount):
    rake_back = get_rake_back(uid)
    set_rake_back(uid, rake_back + amount)

def add_gems(uid, gems):
    try:
        current_gems = get_gems(uid)
        set_gems(uid, current_gems + gems)
    except:
        pass

def add_rain_earn(uid, rain_earnings):
    try:
        current_rain_earn = get_rain_earn(uid)
        set_rain_earn(uid, current_rain_earn + rain_earnings)
    except:
        pass

def discord_timestamp_minutes_ago(minutes_ago):
    current_time = int(time.time())  # Current UNIX timestamp
    target_time = current_time - (minutes_ago * 60)  # Subtract minutes in seconds
    return f"<t:{target_time}:R>"  # Discord relative timestamp format

def subtract_gems(uid, gems):
    try :
        current_gems = get_gems(uid)
        set_gems(uid, current_gems - gems)
    except:
        pass

def set_crash_join(uid, amount):
    data = readdata()
    data['users'][uid]['CrashJoinAmount'] = amount
    writedata(data)

def get_crash_join_amount(uid):
    data = readdata()
    return data['users'][uid]['CrashJoinAmount']

def add_suffix(inte):
    gems = inte
    abs_gems = abs(gems)  # Use absolute value for formatting

    if abs_gems >= 1000000000000000:
        gems_formatted = f"{gems / 1000000000000000:.1f}Q"
    elif abs_gems >= 1000000000000:  # if gems are greater than or equal to 1 trillion
        gems_formatted = f"{gems / 1000000000000:.1f}T"  # display gems in trillions with one decimal point
    elif abs_gems >= 1000000000:  # if gems are greater than or equal to 1 billion
        gems_formatted = f"{gems / 1000000000:.1f}B"  # display gems in billions with one decimal point
    elif abs_gems >= 1000000:  # if gems are greater than or equal to 1 million
        gems_formatted = f"{gems / 1000000:.1f}M"  # display gems in millions with one decimal point
    elif abs_gems >= 1000:  # if gems are greater than or equal to 1 thousand
        gems_formatted = f"{gems / 1000:.1f}K"  # display gems in thousands with one decimal point
    else:  # if gems are less than 1 thousand
        gems_formatted = str(gems)  # display gems as is

    return gems_formatted
class SystemRainButtons(discord.ui.View):
    def __init__(self, message, entries, amount, ends, emoji):
        super().__init__(timeout=None)
        self.message = message
        self.entries = entries
        self.amount = amount
        self.ends = ends
        self.emoji = emoji
        self.setup_buttons()

    def setup_buttons(self):
        button = discord.ui.Button(label="Join", custom_id=f"join", style=discord.ButtonStyle.green, emoji="✅")
        button.callback = self.button_join
        self.add_item(button)

    async def button_join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        uid = str(interaction.user.id)
        if uid not in self.entries:
            self.entries.append(uid)
            embed = discord.Embed(title=f"{self.emoji} Rain In Progress",
                                  description=f"",
                                  color=0x3471eb)
            embed.set_footer(text=Config['Bot Name'],
                             icon_url=Config['Bot Icon'])
            embed.add_field(name="",
                            value=f":man_pouting: **Host:** <@{interaction.user.id}>\n:gem: **Amount:** {add_suffix(self.amount)}\n:money_mouth: **Entries:** {len(self.entries)}\n:gem: **Gems Per Person:** {add_suffix(self.amount / len(self.entries))}\n:clock1: **Ends:** {self.ends}")
            await self.message.edit(embed=embed,
                               view=SystemRainButtons(amount=self.amount, entries=self.entries,
                                                ends=self.ends,
                                                message=self.message, emoji=self.emoji))

async def system_rain(amount, duration):
    channel = bot.get_channel(int(Config['Rains']['Channel']))
    rains.append([])
    rain = rains[-1]
    joined = 0
    if joined == 0:
        joined = 1
    emoji = "🌤️"
    if amount <= 500000000:
        emoji = "🌤️"
    elif amount <= 2000000000:
        emoji = "⛅"
    elif amount <= 5000000000:
        emoji = "🌥️"
    elif amount <= 10000000000:
        emoji = "🌦️"
    elif amount <= 20000000000:
        emoji = "🌧️"
    else:
        emoji = "⛈"
    embed = discord.Embed(title=f"{emoji} Rain In Progress",
                          description=f"",
                          color=0x3471eb)
    embed.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    embed.add_field(name="",
                    value=f":man_pouting: **Host:** <@{interaction.user.id}>\n:gem: **Amount:** {add_suffix(amount)}\n:money_mouth: **Entries:** {0}\n:gem: **Gems Per Person:** {add_suffix(amount / joined)}\n:clock1: **Ends:** <t:{round(time.time() + duration)}:R>")
    message = await channel.send(content=".")
    await message.edit(embed=embed,
                       view=SystemRainButtons(amount=amount, entries=rain, ends=f"<t:{round(time.time() + duration)}:R>",
                                             message=message, emoji=emoji))
    await asyncio.sleep(duration)
    embed = discord.Embed(title=":sunny: Rain Ended",
                          description=f"",
                          color=0x3471eb)
    embed.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    embed.add_field(name="",
                    value=f":man_pouting: **Host:** <@{interaction.user.id}>\n:gem: **Amount:** {add_suffix(amount)}\n:money_mouth: **Entries:** {len(rain)}\n:gem: **Gems Per Person:** {add_suffix(amount / len(rain))}")
    await message.edit(embed=embed, view=None)

crash_info = {}
bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())
async def log(text):
    channel = await bot.fetch_channel(Config['Logs'])
    await channel.send(embed=infoe(text))
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1320971317461389333/y7nFDQ_ybux5EB-Jgyk3Ixe0idtYwKXfzZUDzM8iqlMHdfXkrz3kaR2y95h1UMuQmyIu'
BLOCKCYPHER_API_TOKEN = '8f7bb6ff3cb84514a4a98f5f3f2e704c'
LITECOIN_ADDRESS = 'LVWpJvByWQXx6jNizjswi2pJthc9saZtpA'
CALLBACK_URL = 'http://node1.adky.net:1161/webhook'
def subscribe_webhook():
    response = subscribe_to_address_webhook(
        callback_url=CALLBACK_URL,
        subscription_address=LITECOIN_ADDRESS,
        event='unconfirmed-tx',  # Listen for unconfirmed transactions
        api_key=BLOCKCYPHER_API_TOKEN
    )
    print("Webhook subscription created with ID:", response)
@app.route('/webhook', methods=['POST'])
async def handle_webhook():
    print("Raw Request Data:", request.data)  # Print raw data
    try:
        data = await request.json  # Parse the incoming JSON
        print("Parsed JSON Data:", data)  # Print parsed data
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({"error": "Failed to parse JSON"}), 400

    # Extract transaction data
    tx_hash = data.get('hash')
    addresses = data.get('addresses', [])
    total_received = data.get('total', 0) / 1e8  # Convert satoshis to LTC
    print(f"New transaction detected: {tx_hash}")
    print(f"Addresses involved: {addresses}")
    print(f"Total received: {total_received} LTC")

    # Sending data to Discord
    await send_to_discord(tx_hash, total_received, addresses)
    return jsonify({"message": "Webhook received successfully"}), 200

# Function to send the message to Discord channel
async def send_to_discord(tx_hash, total_received, addresses):
    channel_id = 1247965589352349746  # Replace with your actual channel ID
    try:
        channel = bot.get_channel(channel_id)  # Cached channel
        embed = Embed(
            title="New Transaction Detected",
            description=f"A new transaction was detected on your Litecoin address.\n\n"
                        f"**Transaction Hash**: {tx_hash}\n"
                        f"**Total Received**: {total_received} LTC\n"
                        f"**Addresses Involved**: {', '.join(addresses)}",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending to Discord: {e}")


@app.route("/deposit_request", methods=['POST'])
async def deposit_request():
    data = await request.data
    data = json.loads(data)
    gems = data['gems']
    message = data['message']
    print(f"Deposit! Gems: {gems} Code: {message}")
    codes = get_codes()
    print(codes)
    for item in codes:
        if item[1] == message:
            add_gems(str(item[0]), int(gems))
            database = readdata()
            database['users'][str(item[0])]['Deposited'] += int(gems)
            writedata(database)
            print("add")
            remove_code(item)


            await send_webhook_notification(str(item[0]), int(gems))

    return jsonify({"message": "success"}), 200

@app.route("/get_withdraws", methods=['GET'])
async def get_withdraws():
    with open("withdraws.json", "r") as f:
        oldwithdraws = json.loads(f.read())
    with open("withdraws.json", "w") as f :
        f.write("[]")
    return jsonify(oldwithdraws), 200

@bot.event
async def on_ready() :
    print("Bot Is Online And Listening For Commands.")
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")


def get_category_by_name(guild, category_name):
    for category in guild.categories:
        if category.name == category_name:
            return category
    return None

class DepositSelectionView(discord.ui.View):
    def __init__(self, interaction, filtered_username, amount, guild, code):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.filtered_username = filtered_username
        self.amount = amount
        self.guild = guild
        self.code = code

    @discord.ui.select(
        placeholder="Choose deposit type...",
        options=[
            discord.SelectOption(label="Gems", description="Deposit Gems only", emoji="💎"),
            discord.SelectOption(label="RAP", description="Deposit RAP (Huges only)", emoji="🐶"),
            discord.SelectOption(label="Gems + RAP", description="Deposit both Gems and RAP", emoji="💫"),
        ],
    )
    async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        selection = interaction.values[0]  
        channel_name = f"deposit-{self.filtered_username}".lower()

        existing_channel = discord.utils.get(self.guild.channels, name=channel_name)
        if existing_channel:
            await select.response.send_message(
                embed=discord.Embed(
                    title=":x: Error",
                    description="You already have an open deposit channel!",
                    color=0xff0000,
                ),
                ephemeral=True,
            )
            return

        database = readdata()
        category_name = "Deposits"  
        category = get_category_by_name(self.guild, category_name)

        if category is None:
            await select.response.send_message(
                embed=discord.Embed(
                    title=":x: Error",
                    description=f"Category '{category_name}' not found!",
                    color=0xff0000,
                ),
                ephemeral=True,
            )
            return

        new_channel = await self.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites={
                self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                self.interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                self.guild.get_role(1314565811452645432): discord.PermissionOverwrite(view_channel=True, send_messages=True),
            },
        )

        embed = discord.Embed(
            title=":dart: Deposit Request",
            description="",
            color=0x3471eb,
        )
        embed.add_field(
            name="",
            value=(
                f":blond_haired_person: **User:** {self.interaction.user.mention} (`{database['users'][str(self.interaction.user.id)]['linkedusername']}`)\n"
                f":gem: **Deposit Amount:** {self.amount}\n"
                f":ballot_box_with_check: **Selection:** {selection}\n\n"
                f"**Please wait for someone to assist you, if you wish to close your deposit request use /close command**"),
        )
        embed.set_footer(text="Gambling Paradise")
        await new_channel.send(
            content=f"<@&1314565811452645432>, {self.interaction.user.mention}",  # replace those numbers with the role id you want :) 
            embed=embed,
        )
        await select.response.send_message(
            f"Your deposit request has been created in {new_channel.mention}. Please be patient and wait for someone to assist you.",
            ephemeral=True
        )

@bot.tree.command(name="deposit", description="Deposit Some Gems To Gamble")
@app_commands.describe(amount="The amount of gems to deposit.")
async def deposit(interaction: discord.Interaction, amount: str):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))

    if is_registered(str(interaction.user.id)):
        filtered_username = re.sub(r"[^a-zA-Z0-9]", "", interaction.user.name)
        random_words = random.sample(words, 3)
        code = " ".join(random_words)
        add_code([str(interaction.user.id), code])

        view = DepositSelectionView(interaction, filtered_username, amount, interaction.guild, code)

        await interaction.response.send_message(
            f"To continue please select your deposit method:", view=view, ephemeral=True)

@bot.tree.command(name="close", description="Close your deposit channel")
async def close(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user

    
    special_role_name = "💎 Deposit/Withdraw Team" # put mame of the role here

    
    special_role = discord.utils.get(guild.roles, name=special_role_name)
    has_special_role = special_role in user.roles if special_role else False

   
    filtered_username = "".join(c for c in user.name if c.isalnum() or c == '-').lower()
    user_channel_name = f"deposit-{filtered_username}"

    
    if interaction.channel.name != user_channel_name and not has_special_role:
        await interaction.response.send_message(
            embed=discord.Embed(
                title=":x: Error",
                description="You can only close your own deposit channel unless you have the appropriate role!",
                color=0xff0000
            ),
            ephemeral=True
        )
        return

   
    await interaction.channel.delete(reason=f"Deposit channel closed by {user.name}")

    
    try:
        await user.send(
            embed=discord.Embed(
                title=":white_check_mark: Channel Closed",
                description=f"Deposit channel `{interaction.channel.name}` has been closed.",
                color=0x00ff00
            )
        )
    except discord.Forbidden:
        pass

@bot.tree.command(name="botstats", description="Bot's stats")
async def botstats(interaction: discord.Interaction):
    try:
        with open("data.json", "r") as file:
            data = json.load(file)

        users = data.get("users", {})
        total_deposited = 0
        total_withdrawn = 0

        for user_id, transactions in users.items():
            total_deposited += transactions.get("Deposited", 0)
            total_withdrawn += transactions.get("Withdrawn", 0)

        registered_users = len(users)
        total_members = interaction.guild.member_count
        online_members = sum(member.status != discord.Status.offline for member in interaction.guild.members)

        deposited_with_suffix = add_suffix(total_deposited)
        withdrawn_with_suffix = add_suffix(total_withdrawn)

        embed = discord.Embed(
            title="Server Stats",
            color=0x0062ff
        )
        embed.add_field(name="Total Members", value=f"{total_members:,}", inline=True)
        embed.add_field(name="Online Members", value=f"{online_members:,}", inline=True)
        embed.add_field(name="Registered Users", value=f"{registered_users:,}", inline=True)
        embed.add_field(name="Total Deposited", value=f"{deposited_with_suffix} <:gem:1206711353176498197>", inline=True)
        embed.add_field(name="Total Withdrawn", value=f"{withdrawn_with_suffix} <:gem:1206711353176498197>", inline=True)

        embed.set_footer(text=f"{Config['Bot Name']}", icon_url=Config["Bot Icon"])
        embed.set_thumbnail(url=Config["Bot Icon"])  # Customize thumbnail to match the bot's branding

        await interaction.response.send_message(embed=embed)

    except FileNotFoundError:
        await interaction.response.send_message(
            "Error: `data.json` file does not exist.",
            ephemeral=True
        )
    except json.JSONDecodeError:
        await interaction.response.send_message(
            "Error: `data.json` contains invalid JSON.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"An unexpected error occurred: {e}", ephemeral=True
        )


TRANSACTION_FILE = "history.json"

def load_history():
    try:
        with open(TRANSACTION_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_history(history):
    with open(TRANSACTION_FILE, "w") as file:
        json.dump(history, file, indent=4)

# Transaction logging function
def log_transaction(user_id, description):
    history = load_history()
    timestamp = int(datetime.now(timezone.utc).timestamp())  # Unix timestamp as an integer
    record = f"{description} | {timestamp}"

    if user_id not in history:
        history[user_id] = []
    history[user_id].insert(0, record)  # Add new record to the beginning
    save_history(history)

# History View for Pagination
class HistoryView(discord.ui.View):
    def __init__(self, user_id, user_history):
        super().__init__(timeout=60)  # Timeout for button interaction
        self.user_id = user_id
        self.user_history = user_history
        self.page = 1
        self.transactions_per_page = 10
        self.total_pages = math.ceil(len(self.user_history) / self.transactions_per_page)

    async def update_embed(self, interaction):
        """Updates the embed with the current page."""
        start_idx = (self.page - 1) * self.transactions_per_page
        end_idx = start_idx + self.transactions_per_page
        transactions_on_page = self.user_history[start_idx:end_idx]

        # Build description with one-line entries
        description_lines = []
        for record in transactions_on_page:
            description, timestamp = record.split(" | ")
            description_lines.append(f"- **{description} |**<t:{timestamp}:R>")
        description = "\n".join(description_lines)

        embed = discord.Embed(
            title="Transaction History",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page}/{self.total_pages}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            self.page -= 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()  # Ignore invalid interactions

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            self.page += 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()  # Ignore invalid interactions

# History Command
@bot.tree.command(name="history", description="View your transaction history.")
async def history(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    transaction_history = load_history()
    user_history = transaction_history.get(user_id, [])

    if not user_history:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="No Transaction History",
                description="You have no recorded transactions.",
                color=discord.Color.red()
            ),
            ephemeral=False
        )
        return

    # Create the view and embed for the first page
    view = HistoryView(user_id, user_history)
    start_idx = (view.page - 1) * view.transactions_per_page
    end_idx = start_idx + view.transactions_per_page
    transactions_on_page = user_history[start_idx:end_idx]

    # Build description with one-line entries
    description_lines = []
    for record in transactions_on_page:
        description, timestamp = record.split(" | ")
        description_lines.append(f"- **{description} |** <t:{timestamp}:R>")
    description = "\n".join(description_lines)

    embed = discord.Embed(
        title="Transaction History",
        description=description,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Page {view.page}/{view.total_pages}")
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)



def get_ltc_to_usd():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        if 'litecoin' in data and 'usd' in data['litecoin']:
            return data['litecoin']['usd']
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching LTC to USD rate: {str(e)}")
        return None

@bot.tree.command(name="claimroles", description="Claim your wager roles")
async def claimroles(interaction: discord.Interaction):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))

    uid = str(interaction.user.id)
    data_base = readdata()
    twagered = data_base['users'][uid].get('Wagered', 0)  

    roles_to_claim = [
        {"name": "🐋 Whale", "wager_condition": 250000000},
        {"name": "🐙 Kraken", "wager_condition": 500000000},
        {"name": "🦈 Shark", "wager_condition": 1000000000},
        {"name": "🛳️ Titanic", "wager_condition": 10000000000},
        {"name": "🐉 Dragon", "wager_condition": 20000000000}
    ]

    claimed_roles = []
    user_roles = [role.name for role in interaction.user.roles]

    for role_info in roles_to_claim:
        role_name = role_info["name"]
        wager_condition = role_info["wager_condition"]

        if twagered >= wager_condition:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    claimed_roles.append(role)
                elif role.name in user_roles:
                    claimed_roles.append(role)

    embed = discord.Embed(
        title=f"Claimed Roles.",
        color=0x0062ff)

    if claimed_roles:
        embed.add_field(name="The following roles have been claimed:", value="\n".join([f"- {role.mention}" for role in claimed_roles]), inline=False)
        embed.set_footer(text=Config["Bot Name"])
    else:
        embed.add_field(name="The following roles have been claimed:", value="\n", inline=False)
        embed.set_footer(text=Config["Bot Name"])

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="link", description="Link your username")
async def link(interaction: discord.Interaction, username: str):
    uid = str(interaction.user.id)
    if not is_registered(uid):
        register_user(uid)
        embed = discord.Embed(title=":x: Error",
                              description="You are not registered!",
                              color=0xff0000)
        embed.set_footer(text=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return
    

    set_linkedusername(uid, username)


    embed = discord.Embed(title=":white_check_mark: Account linked",
                          description=f"Successfully linked your Roblox username: `{username}` to your discord account.",
                          color=0x0062ff)
    embed.set_footer(text="/link - To link another account run /link again",
                     icon_url=Config['Bot Icon'])
    await interaction.response.send_message(embed=embed)


def get_transaction_status(address):
    try:
        response = requests.get(f"https://apirone.com/api/v2/wallets/{wallet_id}/addresses/{address}/transactions")
        transactions = response.json().get("transactions", [])
        return transactions
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

def get_transaction_confirmation_status(txid):
    try:
        response = requests.get(f"https://apirone.com/api/v2/transactions/{txid}")
        transaction = response.json()
        return transaction.get("confirmations", 0)
    except Exception as e:
        print(f"Error getting confirmation status: {e}")
        return 0

def genaddress():
    ad = requests.post(f"https://apirone.com/api/v2/wallets/{wallet_id}/addresses").json()
    address = ad["address"]
    return address

def get_address_balance(address):
            try:
                response = requests.get(f"https://apirone.com/api/v2/wallets/{wallet_id}/addresses/{address}/balance")
                return float(response.json()["total"]) / 100000000  # Conversion satoshis -> LTC
            except:
                return None

wallet_id = ""
transfer_key = ""
@bot.tree.command(name="deposit-ltc", description="Deposit Litecoin (LTC) and earn gems!")
@app_commands.describe(amount="The amount in USD you want to deposit")
async def deposit(interaction: discord.Interaction, amount: float):
    try:
        RATE = 2.5
        betchannel_id = 1202733926427398144

        if amount <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(color=0xFF0000, title="Invalid Amount", description="Amount must be greater than 0."),
                ephemeral=True
            )
            return

        if interaction.channel_id != betchannel_id:
            await interaction.response.send_message(
                embed=discord.Embed(color=0x26d394, title="Wrong Channel", description="Use this command in the designated channel."),
                ephemeral=True
            )
            return

        address = genaddress()
        invoice = discord.Embed(color=0x26d394, title="Deposit Instructions")
        invoice.add_field(name="Litecoin (LTC) Address", value=f"```{address}```", inline=False)
        invoice.add_field(name="Details", value=f"Deposit **${amount:.2f}** worth of Litecoin to this address.", inline=False)
        await interaction.response.send_message(embed=invoice, ephemeral=True)

        # Start monitoring the transactions for this address
        prev_balance = get_address_balance(address)
        transaction_found = False
        while not transaction_found:
            transactions = get_transaction_status(address)
            for tx in transactions:
                if tx["status"] == "confirmed":
                    transaction_found = True
                    txid = tx["txid"]
                    print(f"[DEBUG] Transaction found with txid: {txid}. Waiting for confirmations...")

                    # Wait for enough confirmations (e.g., 6 confirmations)
                    confirmations = 0
                    while confirmations < 6:  # 6 confirmations is typically considered safe
                        confirmations = get_transaction_confirmation_status(txid)
                        await asyncio.sleep(5)  # Check every 5 seconds
                    print(f"[DEBUG] Transaction confirmed with {confirmations} confirmations.")
                    break
            await asyncio.sleep(5)  # Poll every 5 seconds for a new transaction

        # Proceed with gem calculations once the transaction is confirmed
        balance = get_address_balance(address)
        ltc_price = requests.get("https://api.coinbase.com/v2/prices/LTC-USD/buy").json()["data"]["amount"]
        deposited_usd = balance * float(ltc_price)
        gems_received = int((deposited_usd / RATE) * 500000000)
        uid = str(interaction.user.id)

        print(f"[DEBUG] UID: {uid}, Gems to Add: {gems_received}")
        add_gems(uid, gems_received)
        updated_gems = get_gems(uid)
        print(f"[DEBUG] Updated Gems for {uid}: {updated_gems}")

        # Webhook notification
        webhook_url = Config["PrivateChannelWebhook"]
        embed = discord.Embed(title="Gems Added via Deposit", description=f"<@{uid}> received {gems_received} gems.", color=0x00ff00)
        response = requests.post(webhook_url, json={"embeds": [embed.to_dict()]})
        if response.status_code != 200:
            print(f"Webhook failed: {response.status_code}")

        confirmation_embed = discord.Embed(color=0x26d394, title="Deposit Confirmed")
        confirmation_embed.add_field(
            name="Deposit Info",
            value=f"Deposited **${deposited_usd:.2f}**\nReceived **{gems_received} gems**",
            inline=False
        )
        await interaction.user.send(embed=confirmation_embed)

    except Exception as e:
        error_embed = discord.Embed(color=0xFF0000, title="Unexpected Error", description=str(e))
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        print(f"[ERROR] {e}")


@bot.tree.command(name="balance", description="View Your Gem Balance")
async def info(interaction: discord.Interaction, user: discord.Member = None):
    if user:
        interaction.user = user

    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))

    if is_registered(str(interaction.user.id)):
        gems = get_gems(str(interaction.user.id))
        if gems >= 1_000_000_000_000_000:
            gems_formatted = f"{gems / 1_000_000_000_000_000:.1f}Q"
        elif gems >= 1_000_000_000_000:
            gems_formatted = f"{gems / 1_000_000_000_000:.1f}T"
        elif gems >= 1_000_000_000:
            gems_formatted = f"{gems / 1_000_000_000:.1f}B"
        elif gems >= 1_000_000:
            gems_formatted = f"{gems / 1_000_000:.1f}M"
        elif gems >= 1_000:
            gems_formatted = f"{gems / 1_000:.1f}K"
        else:
            gems_formatted = str(gems)

        database = readdata()
        uid = str(interaction.user.id)

        embed = discord.Embed(
            title=f"{interaction.user.name}'s Stats",
            description="",
            color=0x0062ff
        )

        embed.add_field(
            name="Balance",
            value=(
                f"\n\n<:gem:1206711353176498197> **Balance:** {gems_formatted} ({'{:,}'.format(gems)})"
                f"\n<:inbox_tray:1316878195072565329> **Deposited:** {add_suffix(database['users'][uid]['Deposited'])}"
                f"\n<:outbox_tray:1316882691387297823> **Withdrawn:** {add_suffix(database['users'][uid]['Withdrawn'])}"
                f"\n<:gem:1206711353176498197> **Wagered:** {add_suffix(database['users'][uid]['Wagered'])}"
                f"\n<:money_with_wings:1316882748601929758> **Profit:** {add_suffix(database['users'][uid]['Net Profit'])}"
                f"\n<:gem:1206711353176498197> **Linked Account:** {database['users'][uid]['linkedusername']}"
            )
        )

        # Affiliate data
        aff_count = sum(1 for user in database['users'].values() if user.get("Affiliate") == uid)
        affiliate_to = get_affiliate(str(interaction.user.id))
        affiliate_field_value = (
            f"<:gift:1316882809222074458> **Affiliated To:** <@{affiliate_to}>\n"
            f"<:gift:1316882809222074458> **Affiliate Count:** {aff_count}\n"
            f"<:gift:1316882809222074458> **Affiliate Earnings:** {add_suffix(database['users'][uid]['Affiliate Earnings'])}\n"
        ) if affiliate_to else (
            f"<:gift:1316882809222074458> **Affiliated To:** None\n"
            f"<:gift:1316882809222074458> **Affiliate Count:** {aff_count}\n"
            f"<:gift:1316882809222074458> **Affiliate Earnings:** {add_suffix(database['users'][uid]['Affiliate Earnings'])}\n"
        )

        embed.add_field(name="Affiliate", value=affiliate_field_value, inline=False)

        # Extra data
        embed.add_field(
            name="Extra",
            value=(
                f"<:medal:1316882856295006299> **Tips Received:** {add_suffix(database['users'][uid]['Tips Got'])}\n"
                f"<:medal:1316882856295006299> **Tips Sent:** {add_suffix(database['users'][uid]['Tips Sent'])}\n\n"
                f"<:cloud_rain:1316882903875063911> **Total Rained:** {add_suffix(database['users'][uid]['Total Rained'])}\n"
                f"<:cloud_rain:1316882903875063911> **Rain Earnings:** {add_suffix(database['users'][uid]['Rain Earnings'])}"
            )
        )

        embed.set_footer(text="/balance", icon_url=Config['Bot Icon'])

        # Fetch and set thumbnail
        linked_username = database['users'][uid].get("linkedusername")
        if linked_username:
            try:
                # Fetch Roblox user ID from username
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://users.roblox.com/v1/usernames/users",
                        json={"usernames": [linked_username]}
                    ) as roblox_response:
                        roblox_data = await roblox_response.json()
                        if roblox_data["data"]:
                            roblox_user_id = roblox_data["data"][0]["id"]

                            # Fetch headshot image URL
                            async with session.get(
                                "https://thumbnails.roblox.com/v1/users/avatar-headshot",
                                params={"userIds": roblox_user_id, "size": "420x420", "format": "Png"}
                            ) as thumbnail_response:
                                thumbnail_data = await thumbnail_response.json()
                                if thumbnail_data["data"]:
                                    embed.set_thumbnail(url=thumbnail_data["data"][0]["imageUrl"])
                                else:
                                    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else Config['Default Avatar'])
                        else:
                            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else Config['Default Avatar'])
            except Exception:
                embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else Config['Default Avatar'])
        else:
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else Config['Default Avatar'])

        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title=":x: Error",
            description="You Are Not Registered!",
            color=0x0062ff
        )
        embed.set_author(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        embed.set_footer(text="/balance")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Shows bot status")
async def status(interaction: discord.Interaction):
    status_message = Config["Status"]["Message"]
    embed_color = discord.Color.green() if "Online" in status_message else discord.Color.red()
    embed = discord.Embed(title=":white_check_mark: In-game BOT status", description=status_message, color=embed_color)
    embed.set_footer(text=Config['Bot Name'], icon_url=Config['Bot Icon'])
    await interaction.response.send_message(embed=embed)


class RakeButtons(discord.ui.View):
    def __init__(self, i):
        super().__init__(timeout=None)
        self.i = i
        self.setup_buttons()

    def setup_buttons(self):
        button = discord.ui.Button(label="Claim Rakeback", custom_id=f"1", style=discord.ButtonStyle.blurple)
        button.callback = self.button_claim
        self.add_item(button)

    async def button_claim(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        rake_back = get_rake_back(uid)
        set_rake_back(uid, 0)
        add_gems(uid, rake_back)
        embed = discord.Embed(title="Rewards",
                              description=f"- :gem: **{add_suffix(rake_back)} was added to your balance!**\n\n"
                                          "- **Please wager more in order to claim more rewards.**",
                              color=0x0062ff)
        await self.i.edit_original_response(embed=embed, view=None)

@bot.tree.command(name="rakeback", description="View Your Rakeback")
async def rake(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if not is_registered(user_id):
        register_user(user_id)

    rake_back = get_rake_back(user_id)
    if rake_back == 0:
        embed = discord.Embed(title="Rewards",
                              description="```You have no rewards available.\n\n\nPlease wager more gems in order to claim rewards.```",
                              color=0x0062ff)
        embed.set_footer(text=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Rewards",
                              description=f"- :gem: **Rakeback:** *{add_suffix(rake_back)}*\n\n"
                                          "- :moneybag: **Weekly Bonus:** *Coming Soon*\n\n"
                                          "```In order to gain more rewards, you need to wager more.```",
                              color=0x0062ff)
        embed.set_footer(text=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        log_transaction(user_id, f"Rakeback +{add_suffix(rake_back)} 💎")
        await interaction.response.send_message(embed=embed, view=RakeButtons(i=interaction))


@bot.tree.command(name="gamemodes", description="Shows available game modes")
async def gamemodes(interaction: discord.Interaction):
    embed = discord.Embed(title="Available Game Modes (soon more)", color=0x0062ff)
    embed.add_field(name="", value="/mines", inline=False)
    embed.add_field(name="", value="/upgrader", inline=False)
    embed.add_field(name="", value="/flip", inline=False)
    embed.add_field(name="", value="/towers", inline=False)
    embed.add_field(name="", value="/dice", inline=False)
    embed.add_field(name="", value="/blackjack", inline=False)
    embed.set_footer(text="What will you play?")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="roulette", description="Spin the roulette wheel")
async def roulette(interaction: discord.Interaction, bet: str, color: Colors):
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    bet = suffix_to_int(bet)
    uid = str(interaction.user.id)
    gems = bet
    if not is_registered(uid) :
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0xff0000)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="roulette")
        await interaction.response.send_message(embed=embed)
        return
    if get_gems(uid) < bet:
        embed = discord.Embed(title=":x: Error",
                              description="You Cannot Afford This Bet",
                              color=0xff0000)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="roulette")
        await interaction.response.send_message(embed=embed)
        return
    if bet < 999999:
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is 1M",
                              color=0xff0000)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="roulette")
        await interaction.response.send_message(embed=embed)
        return
    won = False
    winnings = 0
    print(color.value)
    if color.name == "Blue":
        won = roll_percentage(45)
        if won:
            winnings = bet*2
            add_gems(uid, gems*2)
    if color.name == "Purple":
        won = roll_percentage(45)
        if won:
            winnings = bet*2
            add_gems(uid, gems*2)
    if color.name == "Gold":
        won = roll_percentage(10)
        if won:
            winnings = bet*8
            add_gems(uid, gems*2)
    timee = time.time()+5
    subtract_gems(uid, gems)
    embed = discord.Embed(title="Roullete",
                          description=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Color Chosen:** {color.name}\n:clock: **Rolling** <t:{round(timee)}:R>", color=0xadadad)
    embed.set_author(name=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    embed.set_footer(text="Good luck!")
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(5)
    if won:
        embed = discord.Embed(title="Roullete Won!",
                              description=f"", color=0x62ff57)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="Good luck!")
        embed.add_field(name="\u200b", value=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Color Chosen:** {color.name}\n:gem: **Winnings:** {add_suffix(winnings)}")
    else:
        embed = discord.Embed(title="Roullete Lost!",
                              description=f"", color=0xff5757)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="Good luck!")
        embed.add_field(name="\u200b", value=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Color Chosen:** {color.name}\n:gem: **Potential Winnings:** {add_suffix(winnings)}")
    await interaction.edit_original_response(embed=embed)


def convert_int_to_abbreviations(input_int):
    abbreviations = [(10**15, 'q'), (10**12, 't'), (10**9, 'b'), (10**6, 'm'), (10**3, 'k')]
    for divisor, abbreviation in abbreviations:
        if input_int >= divisor:
            return f"{input_int / divisor:.1f}{abbreviation}"
    return str(input_int)
 
def convert_abbreviations_to_int(input_str):
    multipliers = {'k': 10**3, 'm': 10**6, 'b': 10**9, 't': 10**12, 'q': 10**15}
    if input_str[-1].lower() in multipliers:
        return int(float(input_str[:-1]) * multipliers[input_str[-1].lower()])
    else:
        return int(input_str)
 
@bot.tree.command(name="slots", description="Play the slot game")
async def slot_game(interaction: discord.Interaction, bet: str):
    bet = convert_abbreviations_to_int(bet)
    user_id = str(interaction.user.id)
    if not is_registered(user_id):
        register_user(user_id)
    gems = get_gems(user_id)
 
    # Check if the bet is valid (i.e., the user has enough gems)
    if bet > gems:
        embed = discord.Embed(title=":x: Error", description="You don't have enough gems to make that bet.", color=0x3471eb)
        await interaction.response.send_message(embed=embed)
        return
    
    # Update the user's total wagered amount
    data = readdata()
    data['users'][user_id]['Wagered'] += bet
    writedata(data)

    emojis = ["🍒", "💎", "💰", "🍀"]
    winning_chances = [0.8, 4, 18, 48]  # chances in percentage to win
 
    winning_weights = [chance / 100 for chance in winning_chances]  # convert chances to weights for winning
 
    # Generate the slots for the first and third row completely randomly
    slots = [random.choices(emojis, k=3) for _ in range(2)]
 
    # Generate the slots for the middle row using the winning weights
    slots.insert(1, random.choices(emojis, winning_weights, k=3))
 
    slot_result = "\n".join([
        " | ".join(slots[0]),
        " | ".join(slots[1]),
        " | ".join(slots[2])
    ])
    embed = discord.Embed(title="🎰 Slot Machine Results 🎰", color=0x3471eb)
    embed.description = f"```\n{slot_result}\n```"
 
    # define the multipliers
    multipliers = [38, 12, 4, 2]
 
    # Calculate the winnings using the winning weights
    winning_slots = slots[1]
    multiplier = 0
    if winning_slots.count("🍒") == 3:
        multiplier = multipliers[0]
    elif winning_slots.count("💎") == 3:
        multiplier = multipliers[1]
    elif winning_slots.count("💰") == 3:
        multiplier = multipliers[2]
    elif winning_slots.count("🍀") == 3:
        multiplier = multipliers[3]
 
    payout = bet * multiplier
 
    embed = discord.Embed(title="🎰 Slot Machine Results 🎰", color=0x3471eb)
    embed.description = f"```\n{slot_result}\n```"
 
    # Update the user's gems
    data['users'][user_id]['Gems'] += payout - bet
    writedata(data)
 
    payout_str = convert_int_to_abbreviations(payout)
    embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Multiplier:** {multiplier}x\n:moneybag: **Profit:** {payout_str}", inline=False)
    embed.set_footer(text="Good luck on your next roll!")
 
    await interaction.response.send_message(embed=embed)


def determine_winner(player_choice, bot_choice):
    if player_choice == bot_choice:
        return "It's a tie!"
    elif (
        (player_choice == "Rock" and bot_choice == "Scissors") or
        (player_choice == "Paper" and bot_choice == "Rock") or
        (player_choice == "Scissors" and bot_choice == "Paper")
    ):
        return "You win!"
    else:
        return "You lose!"
@bot.tree.command(name="rps", description="Rock, Paper, Scissors for a bet")
async def rps(interaction: discord.Interaction, bet: str, choice: RPSSide):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))

    uid = str(interaction.user.id)
    bet = suffix_to_int(bet)

    if bet <= 999999:
        embed = discord.Embed(
            title=":x: Error",
            description="Minimum Bet Is 1M",
            color=0x0062ff
        )
        embed.set_footer(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return

    if bet > get_gems(uid):
        embed = discord.Embed(
            title=":x: Error",
            description="You don't have enough gems to create this bet.",
            color=0x0062ff
        )
        embed.set_footer(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return

    subtract_gems(uid, bet)

    timestamp = (datetime.now() + timedelta(seconds=3)).timestamp()
    embed = discord.Embed(
        title="Rock, Paper, Scissors",
        description=f":clock: **Status:** Choosing <t:{int(timestamp)}:R>...",
        color=0xffa500
    )
    embed.add_field(
        name="Your Choice",
        value=f":gem: **---**",
        inline=False
    )
    embed.add_field(
        name="Bot's Choice",
        value=f":gem: **---**",
        inline=False
    )
    embed.add_field(
        name="Winner",
        value=f"**---** - **---**"
    )


    await interaction.response.send_message(embed=embed)


    await asyncio.sleep(3)

    bot_choice = random.choice([side.value for side in RPSSide])


    result = determine_winner(choice.value, bot_choice)

    new_embed = discord.Embed(
        title="Rock, Paper, Scissors",
        description=f":clock: **Status:** Chosen",
        color=0x0062ff
    )
    new_embed.add_field(
        name="Your Choice",
        value=f":gem: **{choice.value}**",
        inline=False
    )
    new_embed.add_field(
        name="Bot's Choice",
        value=f":gem: **{bot_choice}**",
        inline=False
    )


    if result == "You win!":

        new_embed.add_field(
            name="Winner",
            value=f"{result} - {add_suffix(round(bet * 1.95))}"
        )
        add_gems(uid, round(bet * 1.95))
        add_bet(uid, bet, round(bet * 1.95))
    elif result == "It's a tie!":

        new_embed.add_field(
            name="Result",
            value="It's a tie! No one loses anything."
        )
        add_gems(uid, bet)
        add_bet(uid, bet, 0)
    else:

        new_embed.add_field(
            name="Winner",
            value=f"{result} - {add_suffix(round(bet * 1.95))}"
        )
        add_rake_back(uid, percentage(rb, bet))
        add_bet(uid, bet, 0)


    await interaction.edit_original_response(embed=new_embed)


def get_ltc_price():

    response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd')
    response.raise_for_status()  
    data = response.json()
    return data['litecoin']['usd']

def generate_qr_code_link(usd_amount):

    litecoin_address = 'LNEa82w8dVNRDthjcZ8TxGujN36oiro5WR'


    base_url = 'https://api.qrserver.com/v1/create-qr-code/?size=500x500&data='


    ltc_price = get_ltc_price()


    ltc_amount = usd_amount / ltc_price


    qr_code_text = f'litecoin:{litecoin_address}%3Famount%3D{ltc_amount}'


    full_url = base_url + qr_code_text

    return full_url

@bot.tree.command(name='cashier', description='Generates a QR code link for a Litecoin payment.')
async def cashier(interaction: discord.Interaction, gems: str):

    try:
        gems = suffix_to_int(gems)
    except ValueError:
        try:
            gems = add_suffix(gems)
        except ValueError as e:
            await interaction.response.send_message(str(e))
            return

    if gems < 999999:
        await interaction.response.send_message(embed=fail("The minimum purchase is **1M** Gems"))
        return

    gem_rate = 5.5 / 1000000000
    usd_amount = gems * gem_rate
    ltc_price = get_ltc_price()
    ltc_amount = usd_amount / ltc_price
    qr_code_link = generate_qr_code_link(usd_amount)

    gems_formatted = add_suffix(gems)

    embed = discord.Embed(title='Litecoin Payment QR Code', color=0x0062ff)
    embed.add_field(name='Gems Amount', value=f'{gems_formatted} ({gems:,}) Gems', inline=False)
    embed.add_field(name='Gems To USD', value=f'${usd_amount:.2f}', inline=False)
    embed.add_field(name='LTC Amount', value=f'{ltc_amount:.8f} LTC', inline=False)
    embed.set_footer(text="made by @blinxoo")
    embed.set_image(url=qr_code_link)

    await interaction.response.send_message(embed=embed)


def update_gems(user_id: str, new_balance: int):
    """Update the user's gem balance."""
    database = readdata()
    database['users'][user_id]["Gems"] = new_balance
    writedata(database)


@bot.tree.command(name="leaderboard", description="Top 10 Highest Balances")
async def leaderboard(interaction: discord.Interaction):
    guild = interaction.guild
    users = []  
    for member in guild.members:
        user_id = str(member.id)
        if is_registered(user_id):
            gems = get_gems(user_id)
            users.append((member, gems))


    users.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title=":trophy: Leaderboard - Top 10 Balances",
                          color=0x3471eb)

    for i, (member, gems) in enumerate(users[:10], start=1):
        user_name = member.id
        if gems >= 1000000000000:
            gems_formatted = f"{gems / 1000000000000:.1f}t"
        elif gems >= 1000000000:
            gems_formatted = f"{gems / 1000000000:.1f}b"
        elif gems >= 1000000:
            gems_formatted = f"{gems / 1000000:.1f}m"
        elif gems >= 1000:
            gems_formatted = f"{gems / 1000:.1f}k"
        else:
            gems_formatted = str(gems)

        embed.add_field(
            name=f"",
            value=f"**{i}**: <@{user_name}> :gem: {gems_formatted}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="queue", description="Top Withdrawal Requests")
async def queue(interaction: discord.Interaction):
    with open("withdraws.json", "r") as f:
        withdraws = json.loads(f.read())
        total_gems = sum(withdraw["amount"] for withdraw in withdraws)

    with open("data.json", "r") as f:
        data = json.load(f)

        data = readdata()

    embed = discord.Embed(title="<:withdraw:1316882691387297823> Pending Withdrawals",
                          color=0x0062ff)

    for i, withdraw in enumerate(withdraws, start=1):
        roblox_username = withdraw["user"]
        amount = withdraw["amount"]
        user_mention = withdraw["discorduname"]
        timestamp = withdraw["timestamp"]

        embed.add_field(
            name=f"",
            value=f"- **{roblox_username}** | {add_suffix(amount)} <:gem:1206711353176498197> | Requested <t:{timestamp}:R>",
            inline=False
        )
        embed.set_footer(text=f"{add_suffix(total_gems)}", icon_url=Config['Bot Icon'])

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="affiliate", description="affiliate someone")
async def affiliate(interaction: discord.Interaction, user: discord.Member) :
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    if not is_registered(str(user.id)) :
        register_user(str(user.id))
    database = readdata()
    uid = str(interaction.user.id)
    alreadyaf = database['users'][uid]['Affiliate']
    cf = get_affiliate(uid)
    if cf :
        if interaction.user.id != 1 :
            embed = discord.Embed(title=":x: Affiliation Failed",
                                  description=f"You are already affilaited to <@{alreadyaf}>.",
                                  color=0x0062ff)
            embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
            await interaction.response.send_message(embed=embed)
            return
    if not is_registered(uid) :
        embed = discord.Embed(title=":x: Affiliation Failed",
                              description="You Aren't Registered!",
                              color=0x0062ff)
        embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
        await interaction.response.send_message(embed=embed)
        return
    if user.id == interaction.user.id :
        embed = discord.Embed(title=":x: Affiliation Failed",
                              description="You Can't Affiliate Yourself!",
                              color=0x0062ff)
        embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
        await interaction.response.send_message(embed=embed)
        return
    set_affiliate(uid, str(user.id))
    await log(f"<@{uid}> Affiliated <@{user.id}>")
    add_gems(uid, 250)
    embed = discord.Embed(title="Affiliate Code Redeemed",
                          description=f":rocket: <@{interaction.user.id}> has successfully affiliated to <@{user.id}>!",
                          color=0x0062ff)
    embed.set_footer(text=Config['Bot Name'], icon_url=Config["Bot Icon"])
    

    await interaction.response.send_message(embed=embed)


    webhook_url = Config["Affiliates"]["Webhook"]


    embed_json = {"embeds": [embed.to_dict()]}


    response = requests.post(webhook_url, json=embed_json)
    if response.status_code != 200:
        print(f"Webhook succefully sent. Status code: {response.status_code}")


allowed_user_ids = [str(user_id) for user_id in Config["AdminCommands"]["OwnerID"]]

@bot.tree.command(name="unaffiliate", description="Remove an affiliate from a user")
async def unaffiliate(interaction: discord.Interaction, user: discord.Member):
    uid = str(user.id)
    if str(interaction.user.id) not in allowed_user_ids:
        allowed_users = ", ".join(f"<@{user_id}>" for user_id in allowed_user_ids)
        embed = discord.Embed(
            title=":x: Error",
            description=f"You do not have permission to use this command. Only the following users are allowed: {allowed_users}",
            color=0x0062ff
        )
        await interaction.response.send_message(embed=embed)
        return
    
    data = readdata()
    if data["users"][uid]["Affiliate"] is None:
        embed = discord.Embed(
            title=":x: Unaffiliate Failed",
            description="The target user is not currently affiliated with anyone.",
            color=0x0062ff
        )
        await interaction.response.send_message(embed=embed)
        return
    
    affiliate_id = data["users"][uid]["Affiliate"]
    affiliate_name = bot.get_user(affiliate_id)
    data["users"][uid]["Affiliate"] = None
    writedata(data)
    
    embed = discord.Embed(title=":wastebasket: Affiliate Removed", color=0x3471eb)
    embed.add_field(name="", value=f"Affiliate <@{affiliate_id}> has been unaffiliated from <@{uid}>.")
    embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
    await interaction.response.send_message(embed=embed)


def has_linked_username(uid):
    database = readdata()
    return database['users'][uid]['linkedusername'] is not None



class ConfirmWithdrawView(discord.ui.View):
    def __init__(self, withdraw_entry, webhook_url):
        super().__init__(timeout=None)  # No timeout for the buttons
        self.withdraw_entry = withdraw_entry
        self.webhook_url = webhook_url

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = self.withdraw_entry['discorduname']
        admin_id = str(interaction.user.id)
        admin_data = get_admin_data(admin_id)
        browhat = self.withdraw_entry["amount"]
        if str(interaction.user.id) not in Config['AdminCommands']['UserID']:
            await interaction.response.send_message("You are not authorized to press this button.", ephemeral=True)
            return

        try:
            admin_data['withdrawals'] += 1
            admin_data['withdrawgems'] += browhat
            update_admin_data(admin_id, admin_data)
            gems_formatted = add_suffix(self.withdraw_entry["amount"])
            text_message = f"<@{self.withdraw_entry['discorduname']}> has withdrawn {gems_formatted} :gem:"
            embed = discord.Embed(
                title="✅ Withdraw Confirmed",
                description=f":gem: **Amount:** {gems_formatted}\n:gem: **New Balance:** {add_suffix(get_gems(uid))}",
                color=0x0062ff
            )
            embed.set_author(name=Config["Bot Name"], icon_url=Config["Bot Icon"])
            embed.set_footer(text=f"confirmed by {interaction.user.name}")
            webhook_data = {"content": text_message, "embeds": [embed.to_dict()]}
            response = requests.post(self.webhook_url, json=webhook_data)
            if response.status_code != 200:
                print(f"Failed to send webhook message. Status code: {response.status_code}")

            # Remove the entry from withdraws.json
            with open("withdraws.json", "r") as f:
                withdraws = json.load(f)
            withdraws = [entry for entry in withdraws if entry != self.withdraw_entry]
            with open("withdraws.json", "w") as f:
                json.dump(withdraws, f)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error while confirming withdraw: {e}")
            await interaction.response.send_message("An error occurred while confirming the withdrawal.", ephemeral=True)
            self.stop()  # Stop listening for interactions

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = self.withdraw_entry['discorduname']
        gems_formatted = self.withdraw_entry["amount"]
        if str(interaction.user.id) not in Config['AdminCommands']['UserID']:
            await interaction.response.send_message("You are not authorized to press this button.", ephemeral=True)
            return

        try:
            # Remove the entry from withdraws.json
            with open("withdraws.json", "r") as f:
                withdraws = json.load(f)
            withdraws = [entry for entry in withdraws if entry != self.withdraw_entry]
            with open("withdraws.json", "w") as f:
                json.dump(withdraws, f)
            database = readdata()
            database['users'][uid]['Gems'] += gems_formatted
            database['users'][uid]['Withdrawn'] -= gems_formatted
            writedata(database)

            await interaction.response.send_message(f"The withdrawal has been canceled by <@{str(interaction.user.id)}>", ephemeral=False)
        except Exception as e:
            print(f"Error while canceling withdraw: {e}")
            await interaction.response.send_message("An error occurred while canceling the withdrawal.", ephemeral=True)
            self.stop()  # Stop listening for interactions


@bot.tree.command(name="withdraw", description="Withdraw Gems")
@app_commands.describe(amount="The Amount Of Gems To Withdraw")
async def withdraw(interaction: discord.Interaction, amount: str):
    uid = str(interaction.user.id)

    # Auto-register the user if they are not already registered
    register_user(uid)

    linked_username = get_linkedusername(uid)
    if linked_username is None:
        embed = discord.Embed(
            title=":x: Withdraw Error",
            description="You must link your username using the `/link` command before withdrawing.",
            color=0x0062ff
        )
        await interaction.response.send_message(embed=embed)
        return

    amount = suffix_to_int(amount)
    if get_gems(uid) >= amount:
        if amount >= 15000000:
            subtract_gems(uid, amount)
            gems = amount
            gems_formatted = add_suffix(gems)  # Add suffix formatting

            # Update database with withdrawn amount
            database = readdata()
            database['users'][uid]['Withdrawn'] += gems
            writedata(database)

            # Add withdraw entry to withdraws.json
            with open("withdraws.json", "r") as f:
                old_withdraws = json.load(f)
            withdraw_entry = {
                "discorduname": uid,
                "user": linked_username,
                "amount": amount,
                "timestamp": int(interaction.created_at.timestamp())
            }
            old_withdraws.append(withdraw_entry)
            with open("withdraws.json", "w") as f:
                json.dump(old_withdraws, f)

            # Inform the user that admins will handle their withdrawal
            embed = discord.Embed(
                title="Withdraw Request Submitted",
                description="Your withdraw request is pending admin approval, please wait for an admin to confirm it.",
                color=0x0062ff
            )
            await interaction.response.send_message(embed=embed)

            # Send the confirmation embed with buttons to a specific channel
            admin_channel_id = 1323481340343226469 # Set your admin channel ID here
            admin_channel = interaction.guild.get_channel(admin_channel_id)
            if not admin_channel:
                print(f"Admin channel with ID {admin_channel_id} not found.")
                return

            confirm_embed = discord.Embed(
                title="Withdraw Confirmation",
                description=f"User <@{uid}> has requested a withdrawal.\n\n"
                            f"Amount: **{gems_formatted}** gems\n"
                            f"Username: **{linked_username}**",
                color=0x0062ff
            )
            confirm_embed.set_footer(text="admin only")
            view = ConfirmWithdrawView(withdraw_entry, Config["Withdraws"]["Webhook"])
            await admin_channel.send(embed=confirm_embed, view=view)
        else:
            embed = discord.Embed(
                title=":x: Withdraw Error",
                description="The minimum withdraw amount is **15M gems**",
                color=0x0062ff
            )
            embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title=":x: Withdraw Error",
            description="You don't have enough balance to complete this transaction.",
            color=0x0062ff
        )
        embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
        await interaction.response.send_message(embed=embed)


class WithdrawDropdown(discord.ui.Select):
    def __init__(self, withdraws, webhook_url):
        options = []
        for withdraw in withdraws:
            user = withdraw['user']
            amount = add_suffix(withdraw['amount'])
            timestamp = withdraw['timestamp']
            
            value = f"{user}-{withdraw['amount']}-{timestamp}"[:100]

            options.append(
                discord.SelectOption(
                    label=f"User: {user}, Amount: {amount}"[:100],
                    description=f"Requested: {timestamp}"[:100],
                    value=value
                )
            )

        super().__init__(placeholder="Select a withdrawal to confirm...", options=options)
        self.withdraws = withdraws
        self.webhook_url = webhook_url

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        selected_withdraw = next(
            (withdraw for withdraw in self.withdraws if f"{withdraw['user']}-{withdraw['amount']}-{withdraw['timestamp']}" == selected_value),
            None
        )

        if selected_withdraw:
            await ConfirmWtView.handle_withdrawal(interaction, selected_withdraw, self.webhook_url)
        else:
            await interaction.response.send_message("Selected withdrawal entry not found.", ephemeral=True)



class ConfirmWtView(discord.ui.View):
    def __init__(self, withdraw_entry, webhook_url):
        super().__init__(timeout=None)
        self.withdraw_entry = withdraw_entry
        self.webhook_url = webhook_url

    @staticmethod
    async def handle_withdrawal(interaction: discord.Interaction, withdraw_entry, webhook_url):
        try:
            uid = withdraw_entry['discorduname']
            amount = withdraw_entry["amount"]

            # Update the admin records and format the message
            gems_formatted = add_suffix(amount)
            text_message = f"<@{withdraw_entry['discorduname']}> has withdrawn {gems_formatted} :gem:"
            embed = discord.Embed(
                title="✅ Withdraw Confirmed",
                description=f":gem: **Amount:** {gems_formatted}\n"
                            f":gem: **New Balance:** {add_suffix(get_gems(uid))}",
                color=0x0062ff
            )
            embed.set_author(name=Config["Bot Name"], icon_url=Config["Bot Icon"])
            embed.set_footer(text=f"confirmed by {interaction.user.name}")

            # Send the webhook notification
            webhook_data = {"content": text_message, "embeds": [embed.to_dict()]}
            response = requests.post(webhook_url, json=webhook_data)
            if response.status_code != 200:
                print(f"Failed to send webhook message. Status code: {response.status_code}")

            # Remove the withdrawal entry from `withdraws.json`
            with open("withdraws.json", "r") as f:
                withdraws = json.load(f)
            withdraws = [entry for entry in withdraws if entry != withdraw_entry]
            with open("withdraws.json", "w") as f:
                json.dump(withdraws, f)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error while confirming withdrawal: {e}")
            await interaction.response.send_message("An error occurred while confirming the withdrawal.", ephemeral=True)

class WithdrawDropdownView(discord.ui.View):
    def __init__(self, withdraws, webhook_url):
        super().__init__(timeout=None)  # No timeout for the view
        self.add_item(WithdrawDropdown(withdraws, webhook_url))


@bot.tree.command(name="confirmwithdraw", description="View and confirm pending withdrawals.")
async def confirmwithdraw(interaction: discord.Interaction):
    if str(interaction.user.id) not in Config['AdminCommands']['UserID']:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    with open("withdraws.json", "r") as f:
        withdraws = json.load(f)

    if not withdraws:
        await interaction.response.send_message("There are no pending withdrawals.", ephemeral=True)
        return

    view = WithdrawDropdownView(withdraws, Config["Withdraws"]["Webhook"])
    await interaction.response.send_message("Select a withdrawal to confirm:", view=view, ephemeral=True)


@bot.tree.command(name="tip", description="Send Someone Gems")
@app_commands.describe(user="The User To Send To")
@app_commands.describe(amount="Amount To Send")
async def tip(interaction: discord.Interaction, amount: str, user: discord.Member):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))
    if not is_registered(str(user.id)):
        register_user(str(user.id))

    amount = suffix_to_int(amount)
    if get_gems(str(interaction.user.id)) >= amount and amount >= 1:
        subtract_gems(str(interaction.user.id), amount)
        time.sleep(0.5)
        add_gems(str(user.id), amount)

        database = readdata()
        database['users'][str(interaction.user.id)]['Tips Sent'] += amount
        database['users'][str(user.id)]['Tips Got'] += amount
        writedata(database)

        # Format gems
        if amount >= 1_000_000_000_000:
            gems_formatted = f"{amount / 1_000_000_000_000:.1f}T"
        elif amount >= 1_000_000_000:
            gems_formatted = f"{amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            gems_formatted = f"{amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            gems_formatted = f"{amount / 1_000:.1f}K"
        else:
            gems_formatted = str(amount)

        # Log the transactions
        log_transaction(str(interaction.user.id), f"Tipped -{gems_formatted} 💎")
        log_transaction(str(user.id), f"Received +{gems_formatted} 💎 from {interaction.user.mention}")

        # Create embed for the response
        embed = discord.Embed(title=":gift: Tip Completed", color=0x3471eb)
        embed.add_field(
            name="",
            value=f":gem: **Gems:** {gems_formatted}\n:outbox_tray: **Sender:** <@{interaction.user.id}>\n:inbox_tray: **Receiver:** <@{user.id}>"
        )
        embed.set_footer(text=Config['Bot Name'], icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)

        # Send webhook
        webhook_url = Config["Tips"]["Webhook"]
        text_message = f"<@{interaction.user.id}> has tipped {gems_formatted} to <@{user.id}>"
        embed_json = {"content": text_message, "embeds": [embed.to_dict()]}
        response = requests.post(webhook_url, json=embed_json)
        if response.status_code != 200:
            print(f"Failed to send webhook message. Status code: {response.status_code}")
    else:
        await interaction.response.send_message(
            embed=discord.Embed(
                title=":x: Error",
                description="You don't have enough gems to tip this amount.",
                color=0xff0000
            ),
            ephemeral=True
        )


class RainButtons(discord.ui.View) :
    def __init__(self, message, entries, amount, ends, starter, emoji) :
        super().__init__(timeout=None)
        self.message = message
        self.entries = entries
        self.amount = amount
        self.ends = ends
        self.starter = starter
        self.emoji = emoji
        self.setup_buttons()

    def setup_buttons(self) :
        button = discord.ui.Button(label="Join", custom_id=f"join", style=discord.ButtonStyle.blurple, emoji="💎")
        button.callback = self.button_join
        self.add_item(button)

    async def button_join(self, interaction: discord.Interaction) :
        await interaction.response.defer()
        uid = str(interaction.user.id)
        if not is_registered(str(interaction.user.id)) :
            register_user(str(interaction.user.id))
        found = False
        for person in self.entries:
            print(person)
            if person == uid:
                found = True
        print(found)
        if not found:
            self.entries.append(uid)
            embed = discord.Embed(title=f"{self.emoji} Rain In Progress",
                                  description=f"",
                                  color=0x0062ff)
            embed.set_footer(text=Config['Bot Name'],
                             icon_url=Config['Bot Icon'])
            embed.add_field(name="",
                            value=f":man_pouting: **Host:** <@{self.starter}>\n:gem: **Amount:** {add_suffix(self.amount)}\n:money_mouth: **Entries:** {len(self.entries)}\n:gem: **Gems Per Person:** {add_suffix(self.amount / len(self.entries))}\n:clock1: **Ends:** {self.ends}")
            await self.message.edit(embed=embed,
                               view=RainButtons(amount=self.amount, entries=self.entries,
                                                ends=f"{self.ends}",
                                                message=self.message, starter=self.starter,emoji=self.emoji))


@bot.tree.command(name="rain", description="start a rain")
async def createrain(interaction: discord.Interaction, amount: str, duration: int) :
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    amount = suffix_to_int(amount)
    rci = Config['Rains']['Channel']
    uid = str(interaction.user.id)
    if not is_registered(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="rains")
        await interaction.response.send_message(embed=embed)
        return
    if amount < 99 :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="The minimum rain amount is **100 Gems**",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="rains")
        await interaction.response.send_message(embed=embed)
        return
    if amount > get_gems(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this rain.",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="rains")
        await interaction.response.send_message(embed=embed)
        return
    channel = bot.get_channel(int(Config['Rains']['Channel']))
    rains.append([])
    rain = rains[-1]
    joined = 0
    if joined == 0 :
        joined = 1
    subtract_gems(uid, amount)

    # Update the database with the amount rained by the user
    database = readdata()
    database['users'][uid]['Total Rained'] += amount
    writedata(database)

    emoji = "🌧️"
    embed = discord.Embed(title=f"{emoji} Rain In Progress",
                          description=f"",
                          color=0x0062ff)
    embed.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    embed.add_field(name="",
                    value=f":man_pouting: **Host:** <@{interaction.user.id}>\n:gem: **Amount:** {add_suffix(amount)}\n:money_mouth: **Entries:** {0}\n:gem: **Gems Per Person:** {add_suffix(amount / joined)}\n:clock1: **Ends:** <t:{round(time.time() + duration)}:R>")
    message = await channel.send(content="** **")
    await message.edit(embed=embed,
                       view=RainButtons(amount=amount, entries=rain, ends=f"<t:{round(time.time() + duration)}:R>",
                                        message=message, starter=uid,emoji=emoji))
    embed2 = discord.Embed(title="Rain Created", description=f":gem: **Amount:** {add_suffix(amount)}\n:clock1: **Duration:** {duration}s\n:speech_balloon: **Channel:** <#{rci}>", color=0x0062ff)
    embed2.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    await interaction.response.send_message(embed=embed2)
    await asyncio.sleep(duration)
    if len(rain) == 0:
        gpp = amount
    else:
        gpp = amount / len(rain)
    for person in rain:
        add_gems(person, gpp)
        add_rain_earn(person, gpp)
    embed = discord.Embed(title=":sunny: Rain Ended",
                          description=f":man_pouting: **Host:** <@{interaction.user.id}>\n:gem: **Amount:** {add_suffix(amount)}\n:money_mouth: **Entries:** {len(rain)}\n:gem: **Gems Per Person:** {add_suffix(amount / len(rain))}",
                          color=0x0062ff)
    embed.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    await message.edit(embed=embed, view=None)


class MinesButtons(discord.ui.View) :
    def __init__(self, board, bombs, bet, userboard, usersafes, interaction, exploded) :
        super().__init__(timeout=500)
        self.board = board
        self.bombs = bombs
        self.usersafes = usersafes
        self.bet = bet
        self.userboard = userboard
        self.interaction = interaction
        self.exploded = exploded
        self.setup_buttons()
        self.buttons = {}

    def setup_buttons(self) :
        if not self.exploded :
            for row in range(0, 5) :
                for column in range(0, 5) :
                    square = self.userboard[row][column]
                    if square == "" :
                        button = discord.ui.Button(label="\u200b", custom_id=f"{row} {column}",
                                                   style=discord.ButtonStyle.gray)
                        button.callback = self.button_callback
                        self.add_item(button)
                    if square == "s" :
                        button = discord.ui.Button(label="", custom_id=f"{row} {column}",
                                                   style=discord.ButtonStyle.green, emoji="💎")
                        button.callback = self.button_cashout
                        self.add_item(button)
        else :
            for row in range(0, 5) :
                for column in range(0, 5) :
                    square = self.board[row][column]
                    if square == "" :
                        button = discord.ui.Button(label="\u200b", custom_id=f"{row} {column}",
                                                   style=discord.ButtonStyle.gray)
                        button.callback = self.button_callback
                        button.disabled = True
                        self.add_item(button)
                    if square == "s" :
                        button = discord.ui.Button(label="", custom_id=f"{row} {column}",
                                                   style=discord.ButtonStyle.green, emoji="💎")
                        button.callback = self.button_cashout
                        button.disabled = True
                        self.add_item(button)
                    if square == "m" :
                        button = discord.ui.Button(label="", custom_id=f"{row} {column}", style=discord.ButtonStyle.red,
                                                   emoji="💣")
                        button.callback = self.button_cashout
                        button.disabled = True
                        self.add_item(button)

    async def button_cashout(self, interaction: discord.Interaction) :
        if interaction.user.id == self.interaction.user.id :
            await interaction.response.defer()
            multi = round(calculate_mines_multiplier(self.bombs, self.usersafes, MineHouseEdge), 2)
            add_gems(str(interaction.user.id), round(self.bet * multi))
            add_bet(str(interaction.user.id), self.bet, round(self.bet * multi))
            embed = discord.Embed(color=0x0062ff, title=f":bomb: {self.bombs} Mines Cashed Out",
                                  description="")
            embed.add_field(name="",
                            value=f":gem: **Bet:** {add_suffix(self.bet)}\n:star: **Multiplier:** {round(multi, 2)}x\n:moneybag: **Winnings:** {add_suffix(round(self.bet * multi))}\n")
            embed.set_footer(text=Config["Bot Name"])
            await self.interaction.edit_original_response(
                embed=embed,
                view=MinesButtons(bet=self.bet, board=self.board, bombs=self.bombs, interaction=self.interaction,
                                  usersafes=self.usersafes, userboard=self.userboard, exploded=True))

    async def button_callback(self, interaction: discord.Interaction) :
        if interaction.user.id == self.interaction.user.id :
            custom_id = interaction.data["custom_id"]
            row = int(custom_id.split(" ")[0])
            collum = int(custom_id.split(" ")[1])
            if self.board[row][collum] == "s" :
                safe = True
                self.userboard[row][collum] = "s"
                self.usersafes = self.usersafes + 1
                multi = round(calculate_mines_multiplier(self.bombs, self.usersafes, MineHouseEdge), 2)
                embed = discord.Embed(color=0x0062ff, title=f":gem: Mines",
                                      description="")
                embed.add_field(name="",
                                value=f":gem: **Bet:** {add_suffix(self.bet)}\n:star: **Multiplier:** {round(multi, 2)}x\n:moneybag: **Current Winnings:** {add_suffix(round(self.bet*multi))}\n")
                embed.set_footer(text=Config["Bot Name"])
                await self.interaction.edit_original_response(
                    embed=embed,
                    view=MinesButtons(bet=self.bet, board=self.board, bombs=self.bombs, interaction=self.interaction,
                                      usersafes=self.usersafes, userboard=self.userboard, exploded=False))
            if self.board[row][collum] == "m" :
                add_rake_back(str(self.interaction.user.id), percentage(rb, self.bet))
                add_bet(str(self.interaction.user.id), self.bet, 0)
                embed = discord.Embed(color=0x0062ff, title=f":boom: Bomb Exploded!",
                                      description="")
                multi = round(calculate_mines_multiplier(self.bombs, self.usersafes, MineHouseEdge), 2)
                embed.add_field(name="",
                                value=f":gem: **Bet:** {add_suffix(self.bet)}\n:star: **Multiplier:** {round(multi, 2)}x\n:moneybag: **Potential Winnings:** {add_suffix(round(self.bet*multi))}")
                embed.set_footer(text=Config["Bot Name"])
                await self.interaction.edit_original_response(
                    embed=embed,
                    view=MinesButtons(bet=self.bet, board=self.board, bombs=self.bombs, interaction=self.interaction,
                                      usersafes=self.usersafes, userboard=self.userboard, exploded=True))
            await interaction.response.defer()


@bot.tree.command(name="mines", description="Start A Game Of Mines")
async def mines(interaction: discord.Interaction, bet: str, bombs: int) :
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    valid = True
    uid = str(interaction.user.id)
    bet = suffix_to_int(bet)
    if not is_registered(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return
    if bet <= 999999 :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is **1M** gems.",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return
    if bet > get_gems(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this game.",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        await interaction.response.send_message(embed=embed)
        return
    if bombs >= 25 or bombs <= 0 :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="Invalid Number Of Mines",
                              color=0x0062ff)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if valid :
        subtract_gems(uid, bet)
        af = get_affiliate(str(interaction.user.id))
        add_gems(af, bet * 0.01)
        db = readdata()
        try:
            db['users'][af]['Affiliate Earnings'] += bet*0.01

            interaction_user_name = interaction.user.id
            embed = discord.Embed(title="🔥 Someone gambled with an affiliate code!", color=discord.Color.orange())
            embed.description = f"💎 **Amount:** {add_suffix(bet)}\n💎 **Referer Received:** {add_suffix(bet * 0.01)}\n🤝 **Referer:** <@{af}>\n🤝 **Gambler:** <@{interaction_user_name}>"
            send_webhook(embed)
        except:
            pass
        writedata(db)
        board = generate_board(bombs)
        userboard = [
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
        ]
        coollooking = '\n'.join([' '.join(sublist) for sublist in board])
        await log(f"{interaction.user.name} Started A Mines Game! Board:\n\n{coollooking}")
        embed = discord.Embed(color=0x0062ff, title=f":bomb: {bombs} Mines", description="")
        embed.set_footer(text=Config["Bot Name"])
        embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Multiplier:** 1.00x\n:moneybag: **Current Winnings:**  {add_suffix(bet)}")
        await interaction.response.send_message(
            embed=embed,
            view=MinesButtons(bet=bet, board=board, bombs=bombs, interaction=interaction, usersafes=0,
                              userboard=userboard, exploded=False))

# Function to convert suffix to int (like 10b -> 10000000000)
def suffix_to_int(value):
    suffixes = {'k': 10**3, 'm': 10**6, 'b': 10**9, 't': 10**12}
    if value[-1].lower() in suffixes:
        return int(float(value[:-1]) * suffixes[value[-1].lower()])
    return int(value)                              

def format_number(amount):
    """Format numbers with suffixes for easier readability."""
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.1f}B"  # Billion
    elif amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M"  # Million
    elif amount >= 1_000:
        return f"{amount / 1_000:.1f}K"  # Thousand
    return str(amount)

class TowersButtons(discord.ui.View) :
    def __init__(self, bet, interaction) :
        super().__init__(timeout=500)
        self.bet = bet
        self.interaction = interaction
        self.buttons = [[], [], [], [], []]
        self.layer = 0
        self.multi = 1
        self.cash = None
        self.setup_buttons()

    def setup_buttons(self) :
        for layer in range(0, 5) :
            for tower in range(0, 3) :
                button = discord.ui.Button(label=f"{add_suffix(round(Config['Towers']['Multis'][layer] * self.multi))}x",
                                           custom_id=f"{layer} {tower}", style=discord.ButtonStyle.gray, row=layer)
                button.callback = self.tower_clicked
                if layer == 0 :
                    button.style = discord.ButtonStyle.blurple
                self.buttons[layer].append(button)
                self.add_item(button)
        button = discord.ui.Button(label=f"Cashout", custom_id=f"cash", style=discord.ButtonStyle.green, row=4)
        button.callback = self.cash_clicked
        self.cash = button
        self.add_item(button)

    async def cash_clicked(self, interaction: discord.Interaction) :
        if interaction.user.id == self.interaction.user.id :
            await interaction.response.defer()
            winnings = round(self.bet * self.multi)
            add_gems(str(self.interaction.user.id), winnings)
            add_bet(str(self.interaction.user.id), self.bet, winnings)
            af = get_affiliate(str(self.interaction.user.id))
            for i2 in self.buttons :
                for i3 in i2 :
                    i3.disabled = True
            self.cash.disabled = True
            embed = discord.Embed(title=":white_check_mark: Cashed Out",
                                  description="",
                                  color=0x3471eb)
            embed.add_field(name="",value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(winnings)}\n :star: **Multiplier:** {add_suffix(self.multi)}")
            await self.interaction.edit_original_response(
                embed=embed,
                view=self)

    async def tower_clicked(self, interaction: discord.Interaction) :
        if interaction.user.id == self.interaction.user.id :
            await interaction.response.defer()
            customid = interaction.data["custom_id"]
            layer = int(customid.split(" ")[0])
            tower = int(customid.split(" ")[1])
            print(layer)
            print(self.layer)
            if layer == self.layer :
                for tower2 in self.buttons[layer] :
                    tower2.disabled = True
                    tower2.style = discord.ButtonStyle.gray
                if layer != 4 :
                    for tower2 in self.buttons[layer + 1] :
                        tower2.style = discord.ButtonStyle.blurple
                if roll_percentage(Config['Towers']['WinChance']) :
                    self.buttons[layer][tower].style = discord.ButtonStyle.green
                    self.multi = Config["Towers"]["Multis"][layer]
                else :
                    self.buttons[layer][tower].style = discord.ButtonStyle.red
                    self.cash.disabled = True
                    await self.interaction.edit_original_response(view=self)
                    for i2 in self.buttons :
                        for i3 in i2 :
                            i3.disabled = True
                    await self.interaction.edit_original_response(view=self)
                    await asyncio.sleep(3)
                    add_rake_back(str(interaction.user.id), percentage(rb, self.bet))
                    add_bet(str(interaction.user.id), self.bet, 0)
                    return
                await self.interaction.edit_original_response(view=self)
                self.layer = self.layer + 1


@bot.tree.command(name="towers", description="Start A Game Of Towers")
async def towers(interaction: discord.Interaction, bet: str) :
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    valid = True
    uid = str(interaction.user.id)
    bet = suffix_to_int(bet)
    if not is_registered(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0xff0000)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet <= 999999 :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is **1M** gems.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet > get_gems(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this game.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if valid :
        subtract_gems(uid, bet)
        af = get_affiliate(str(interaction.user.id))
        add_gems(af, bet * 0.00)
        db = readdata()
        try:
            db['users'][af]['Affiliate Earnings'] += bet*0.00

            interaction_user_name = interaction.user.id
            embed = discord.Embed(title="🔥 Someone gambled with an affiliate code!", color=discord.Color.orange())
            embed.description = f"💎 **Amount:** {add_suffix(bet)}\n💎 **Referer Received:** {bet * 0.00}\n🤝 **Referer:** <@{af}>\n🤝 **Gambler:** <@{interaction_user_name}>"
            send_webhook(embed)
        except :
            pass
        writedata(db)
        await log(f"<@{uid}> Bet {add_suffix(bet)}> On Towers")
        embed = discord.Embed(title="Towers", description="", color=0x3471eb)
        embed.add_field(name="",value=f":gem: **Bet:** {add_suffix(bet)}\n:star: **Multiplier:** *Check Buttons*")
        await interaction.response.send_message(embed=embed, view=TowersButtons(bet=bet, interaction=interaction))


class FlipButtons(discord.ui.View) :
    def __init__(self, msg, bet, side, user) :
        super().__init__(timeout=500)
        self.bet = bet
        self.msg = msg
        self.side = side
        self.user = user
        self.buttons = []
        self.setup_buttons()

    def setup_buttons(self) :
        button = discord.ui.Button(label=f"Join", custom_id=f"join", style=discord.ButtonStyle.green)
        button.callback = self.join_clicked
        self.buttons.append(button)
        self.add_item(button)
        button = discord.ui.Button(label=f"Call Bot", custom_id=f"bot", style=discord.ButtonStyle.blurple)
        button.callback = self.bot
        self.buttons.append(button)
        self.add_item(button)

    async def join_clicked(self, interaction: discord.Interaction) :
        uid = str(interaction.user.id)
        if not is_registered(str(interaction.user.id)) :
            register_user(str(interaction.user.id))
        if get_gems(uid) < self.bet :
            await interaction.response.send_message(content="You don't have enough gems to make that bet.", ephemeral=True)
            return
        if uid == self.user :
            await interaction.response.send_message(content="You can't join your own coinflip.", ephemeral=True)
            return
        await interaction.response.send_message(content="Successfully joined the game.", ephemeral=True)
        for button in self.buttons :
            button.disabled = True
        subtract_gems(uid, self.bet)
        af = get_affiliate(str(interaction.user.id))
        user = (interaction.user.name)
        add_gems(af, self.bet * 0.01)
        db = readdata()
        try:
            db['users'][af]['Affiliate Earnings'] += bet*0.01

            interaction_user_name = interaction.user.id
            embed = discord.Embed(title="🔥 Someone gambled with an affiliate code!", color=discord.Color.orange())
            embed.description = f"💎 **Amount:** {add_suffix(bet)}\n💎 **Referer Received:** {bet * 0.01}\n🤝 **Referer:** <@{af}>\n🤝 **Gambler:** <@{interaction_user_name}>"
            send_webhook(embed)
        except:
            pass
        writedata(db)
        await self.msg.edit(view=self)
        choiches = ["Heads", "Tails"]
        choice = random.choice(choiches)
        embed = discord.Embed(title=f"{user}'s Coinflip", description=f"", color=0x3471eb)
        if self.side == "Heads" :
            embed.add_field(name="", value=f":clock: **Status:** Coin Flipped\n\n:coin: **{self.side}:** <@{self.user}>\n:coin: **Tails:** <@{uid}>\n\n:gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(round(self.bet * 1.95))}")
        if self.side == "Tails" :
            embed.add_field(name="", value=f":clock: **Status:** Coin Flipped\n\n:coin: **{self.side}:** <@{self.user}>\n:coin: **Heads:** <@{uid}>\n\n:gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(round(self.bet * 1.95))}")
        if choice == self.side :
            embed.add_field(name="", value=f":medal: **Winner:** <@{self.user}>", inline=False)
            add_gems(self.user, round(self.bet * 2.05))
            add_bet(self.user, self.bet, round(self.bet * 2.05))
            add_bet(uid, self.bet, 0)
        else :
            embed.add_field(name="", value=f":medal: **Winner:** <@{uid}>", inline=False)
            add_gems(uid, round(self.bet * 1.95))
            add_bet(uid, self.bet, round(self.bet * 1.95))
            add_bet(self.user, self.bet, 0)
            add_rake_back(self.user, percentage(rb, self.bet))
        await self.msg.edit(embed=embed)

    async def bot(self, interaction: discord.Interaction) :
        if not is_registered(str(bot.user.id)):
            register_user(str(bot.user.id))
        user = (interaction.user.name)
        uid = str(bot.user.id)
        await interaction.response.send_message(content="Successfully joined the game.", ephemeral=True)
        for button in self.buttons :
            button.disabled = True
        subtract_gems(uid, self.bet)
        await self.msg.edit(view=self)
        choice = "Tails"
        if self.side == "Heads" :
            if roll_percentage(50 + Config['Coinflip']['House']) :
                choice = "Tails"
            else :
                choice = "Heads"
        if self.side == "Tails" :
            if roll_percentage(50 + Config['Coinflip']['House']) :
                choice = "Heads"
            else :
                choice = "Tails"
        embed = discord.Embed(title=f"{user}'s Coinflip", description=f"", color=0x3471eb)
        if self.side == "Heads" :
            embed.add_field(name="", value=f":clock: **Status:** Coin Flipped\n\n:coin: **{self.side}:** <@{self.user}>\n:coin: **Tails:** <@{uid}>\n\n:gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(round(self.bet * 1.95))}")
        if self.side == "Tails" :
            embed.add_field(name="", value=f":clock: **Status:** Coin Flipped\n\n:coin: **{self.side}:** <@{self.user}>\n:coin: **Heads:** <@{uid}>\n\n:gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(round(self.bet * 1.95))}")
        if choice == self.side :
            embed.add_field(name="", value=f":medal: **Winner:** <@{self.user}>", inline=False)
            add_gems(self.user, round(self.bet * 1.95))
            add_bet(self.user, self.bet, round(self.bet * 1.95))
            add_bet(uid, self.bet, 0)
        else :
            embed.add_field(name="", value=f":medal: **Winner:** <@{uid}>", inline=False)
            add_gems(uid, round(self.bet * 1.95))
            add_rake_back(self.user, percentage(rb, self.bet))
            add_bet(self.user, self.bet, 0)
            add_bet(uid, self.bet, round(self.bet * 1.95))
        await self.msg.edit(embed=embed)


@bot.tree.command(name="flip", description="Coinflip")
async def flip(interaction: discord.Interaction, bet: str, side: CoinSide) :
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    valid = True
    uid = str(interaction.user.id)
    user = (interaction.user.name)
    bet = suffix_to_int(bet)
    if not is_registered(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet <= 999999 :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is **1M** gems.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet > get_gems(uid) :
        valid = False
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this game.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if valid :
        subtract_gems(uid, bet)
        af = get_affiliate(str(interaction.user.id))
        add_gems(af, bet * 0.01)
        db = readdata()
        try:
            db['users'][af]['Affiliate Earnings'] += bet*0.01

            interaction_user_name = interaction.user.id
            embed = discord.Embed(title="🔥 Someone gambled with an affiliate code!", color=discord.Color.orange())
            embed.description = f"💎 **Amount:** {add_suffix(bet)}\n💎 **Referer Received:** {bet * 0.01}\n🤝 **Referer:** <@{af}>\n🤝 **Gambler:** <@{interaction_user_name}>"
            send_webhook(embed)
        except:
            pass
        writedata(db)
        channel = bot.get_channel(int(Config['Coinflip']['1v1']))
        embed = discord.Embed(title=f"{user}'s Coinflip", description=f"", color=0x3471eb)
        if side.value == "Heads" :
            embed.add_field(name="", value=f":clock: **Status:** Waiting for players...\n\n:coin: **{side.value}:** <@{uid}>\n:coin: **Tails:** Undecided\n\n:gem: **Bet:** {add_suffix(bet)}\n:gem: **Potential Winnings:** {add_suffix(round(bet * 1.95))}\n\n:medal: **Winner:** Undecided")
        if side.value == "Tails" :
            embed.add_field(name="", value=f":clock: **Status:** Waiting for players...\n\n:coin: **{side.value}:** <@{uid}>\n:coin: **Heads:** Undecided\n\n:gem: **Bet:** {add_suffix(bet)}\n:gem: **Potential Winnings:** {add_suffix(round(bet * 1.95))}\n\n:medal: **Winner:** Undecided")
        embed.set_footer(text=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        msg = await channel.send(embed=embed)
        await msg.edit(embed=embed, view=FlipButtons(msg, bet, side.value, uid))
        
        # Construct the embed for the confirmation message
        confirmation_embed = discord.Embed(
            title="✅ Coinflip Created",
            description=f"💬 **Channel:** <#{Config['Coinflip']['1v1']}>\n💎 **Amount:** {add_suffix(bet)}",
            color=0x3471eb
        )
        confirmation_embed.set_footer(text=Config['Bot Name'], icon_url=Config['Bot Icon'])

        # Send the confirmation message as a reply
        await interaction.response.send_message(embed=confirmation_embed)
class UpgradeButton(discord.ui.View) :
    def __init__(self, interaction, bet, chance, multiplier, roll=1):
        super().__init__(timeout=500)
        self.interaction = interaction
        self.bet = bet
        self.chance = chance
        self.multiplier = multiplier
        self.roll = roll
        self.setup_buttons()

    def setup_buttons(self) :
        button = discord.ui.Button(label=f"Upgrade", custom_id=f"join", style=discord.ButtonStyle.blurple)
        button.callback = self.join_clicked
        self.add_item(button)
    async def join_clicked(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        af = get_affiliate(uid)
        add_gems(af, self.bet * 0.01)
        db = readdata()
        try :
            db['users'][af]['Affiliate Earnings'] += self.bet * 0.01
        except :
            pass
        print("1")
        if uid != str(self.interaction.user.id):
            return
        print("2")
        if self.bet > get_gems(uid):
            await self.interaction.edit_original_response(embed=fail("You Can No Longer Afford This Bet"),view=None)
            return
        print("3")
        subtract_gems(uid,self.bet)
        won = roll_percentage(self.chance)

        if won:
            print("4")
            add_gems(uid, round(self.bet*self.multiplier))
            add_bet(uid, self.bet, self.bet*self.multiplier)
            embed = discord.Embed(title=":white_check_mark: Upgrade Won",description="",color=0x4dff58)
            embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(round(self.bet*self.multiplier))}\n:four_leaf_clover: **Win Chance:** {round(self.chance, 1)}%\n:star: **Multiplier:** x{self.multiplier}")
            embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
            await self.interaction.edit_original_response(embed=embed, view=None)
        else:
            print("5")
            add_bet(uid, self.bet, 0)
            embed = discord.Embed(title=":x: Upgrade Lost",description="",color=0xff0000)
            embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Lost Winnings:** {add_suffix(round(self.bet*self.multiplier))}\n:four_leaf_clover: **Win Chance:** {round(self.chance, 1)}%\n:star: **Multiplier:** x{self.multiplier}")
            embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
            await self.interaction.edit_original_response(embed=embed, view=None)

green = 0x4dff58
red = 0xff6b6b
yellow = 0xfff93d

@bot.tree.command(name="upgrader", description="Put Some Gems In The Upgrade Machine!")
async def upgrade(interaction: discord.Interaction, bet: str, multiplier: float):
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    bet = suffix_to_int(bet)
    uid = str(interaction.user.id)
    if not is_registered(uid) :
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="cases")
        await interaction.response.send_message(embed=embed)
        return
    if multiplier < 1.7:
        embed = discord.Embed(title=":x: Error",
                              description="The multiplier cannot be under **1.7**",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="cases")
        await interaction.response.send_message(embed=embed)
        return
    if get_gems(uid) < bet:
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this game.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="cases")
        await interaction.response.send_message(embed=embed)
        return
    if bet < 999999:
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is **1M** gems.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'],
                         icon_url=Config['Bot Icon'])
        embed.set_footer(text="cases")
        await interaction.response.send_message(embed=embed)
        return
    embed = discord.Embed(title="Upgrader", description="",color=0x3471eb)
    win_chance = multiplier_to_percentage(multiplier,Config['Upgrader']['House'])
    winnings = round(bet*multiplier)
    embed.add_field(name="",value=f":gem: **Bet:** {add_suffix(bet)}\n:gem: **Potential Winnings:** {add_suffix(winnings)}\n:four_leaf_clover: **Win Chance:** {round(win_chance, 1)}%\n:star: **Multiplier:** x{multiplier}")
    embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])

    log_transaction(uid, f"Upgrader {add_suffix(bet)} 💎")
    await interaction.response.send_message(embed=embed,view=UpgradeButton(interaction,bet,win_chance,multiplier))


# Define the base deck of cards
basedeck = [ 
    "2♠", "3♠", "4♠", "5♠", "6♠", "7♠", "8♠", "9♠", "10♠", "J♠", "Q♠", "K♠", "A♠",
    "2♥", "3♥", "4♥", "5♥", "6♥", "7♥", "8♥", "9♥", "10♥", "J♥", "Q♥", "K♥", "A♥",
    "2♦", "3♦", "4♦", "5♦", "6♦", "7♦", "8♦", "9♦", "10♦", "J♦", "Q♦", "K♦", "A♦",
    "2♣", "3♣", "4♣", "5♣", "6♣", "7♣", "8♣", "9♣", "10♣", "J♣", "Q♣", "K♣", "A♣"
]

def card_to_value(card):
    if "10" in card:
        return 10
    card = card[0]
    if card == "J":
        return 10
    if card == "Q":
        return 10
    if card == "K":
        return 10
    if card == "A":
        return 11
    return int(card)

def hand_to_value(hand):
    total_value = 0
    aces = 0

    # Calculate the initial value of the hand, counting Aces as 11
    for card in hand:
        card_value = card_to_value(card)
        total_value += card_value
        if card_value == 11:  # This means the card is an Ace
            aces += 1

    # Adjust the value of Aces from 11 to 1 as needed
    while total_value > 21 and aces:
        total_value -= 10  # Treat one Ace as 1 instead of 11
        aces -= 1

    return total_value

def pick_card(deck):
    if not deck:
        return None, deck  # Return None and the unchanged deck if it's empty
    card = random.choice(deck)
    deck.remove(card)
    return card, deck

def render_blackjack_hand(hand, hide):
    Hstr = ""
    Hvalue = hand_to_value(hand)
    for card in hand:
        Hstr += f"{card}  "
    Hstr += f"\nPlayer's Card Value: {Hvalue}"
    return Hstr

class BJButton(discord.ui.View):
    def __init__(self, interaction, bet, user_hand, dealer_hand, deck):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.bet = bet
        self.user_hand = user_hand
        self.dealer_hand = dealer_hand
        self.deck = deck
        self.buttons = []
        self.setup_buttons()

    def setup_buttons(self):
        button = discord.ui.Button(label=f"Hit", custom_id=f"hit", style=discord.ButtonStyle.green)
        button.callback = self.hit_clicked
        self.buttons.append(button)
        self.add_item(button)
        button = discord.ui.Button(label=f"Stand", custom_id=f"stand", style=discord.ButtonStyle.red)
        button.callback = self.stand_clicked
        self.buttons.append(button)
        self.add_item(button)
        button = discord.ui.Button(label=f"Double", custom_id=f"double", style=discord.ButtonStyle.blurple)
        button.callback = self.double_clicked
        self.buttons.append(button)
        self.add_item(button)

    async def hit_clicked(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        await interaction.response.defer()  # Defers the response

        # Ensure only the original player can interact
        if uid != str(self.interaction.user.id):
            return

        # Draw a card for the player
        card, self.deck = pick_card(self.deck)
        if card is None:  # Check if the deck is empty
            embed = discord.Embed(title="Error", description="The deck is empty!", color=0xff0000)
            await self.interaction.edit_original_response(embed=embed, view=None)
            return
        
        # Update player's hand
        self.user_hand.append(card)
        
        # Check for bust
        if hand_to_value(self.user_hand) >= 22:
            add_bet(uid, self.bet, 0)  # Adjust user balance for loss
            embed = discord.Embed(title="Blackjack - You Lost!", description="", color=0xff0000)
            embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Lost Winnings:** {add_suffix(self.bet * 2)}")
            embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
            embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
            await self.interaction.edit_original_response(embed=embed, view=None)
            return

        # Update the embed to show the new hand state
        embed = discord.Embed(title="Blackjack", description="", color=0x3471eb)
        embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Potential Winnings:** {add_suffix(self.bet * 2)}")
        embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
        embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
        await self.interaction.edit_original_response(embed=embed, view=self)

    async def stand_clicked(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        await interaction.response.defer()
        if uid != str(self.interaction.user.id):
            return

        await self.interaction.edit_original_response(view=None)

        # Draw cards for the dealer with a delay
        while hand_to_value(self.dealer_hand) < 17:
            await asyncio.sleep(1)  # Wait for 1 second before drawing the next card
            card, self.deck = pick_card(self.deck)
            if card is None:  # Check if the card is None (indicating an empty deck)
                break
            self.dealer_hand.append(card)

            # Update the embed to show the dealer's hand after each card drawn
            embed = discord.Embed(title="Blackjack", color=0x3471eb)
            embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
            embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
            await self.interaction.edit_original_response(embed=embed, view=None)

        # Determine the outcome after the dealer finishes drawing
        user_total = hand_to_value(self.user_hand)
        dealer_total = hand_to_value(self.dealer_hand)

        if dealer_total >= 22 or dealer_total < user_total:
            add_gems(uid, self.bet * 2)  # Player wins, double their bet
            add_bet(uid, self.bet, self.bet * 2)
            result_description = "You Won! 🏆"
            color = 0x00ff00  # Green
        elif dealer_total > user_total:
            add_bet(uid, self.bet, 0)  # Dealer wins, player loses bet
            result_description = "You Lost! 💔"
            color = 0xff0000  # Red
        else:
            add_gems(uid, self.bet)  # Refund the bet on a tie
            add_bet(uid, self.bet, self.bet)  # Record as tie (no profit or loss)
            result_description = "It's a Tie! 🤝"
            color = 0xffff00  # Yellow

        # Final embed message displaying the results
        embed = discord.Embed(title="Blackjack - " + result_description, color=color)
        embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Winnings:** {add_suffix(self.bet if result_description == 'Its a Tie!' else self.bet * 2)}")
        embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
        embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
        await self.interaction.edit_original_response(embed=embed, view=None)

    async def double_clicked(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        await interaction.response.defer()

        if uid != str(self.interaction.user.id):
            return

        if get_gems(uid) < self.bet:
            embed = discord.Embed(
                title=":x: Error",
                description="You don’t have enough gems to double down.",
                color=0xff0000
            )
            await self.interaction.followup.send(embed=embed, ephemeral=True)
            return

        self.bet *= 2
        subtract_gems(uid, self.bet // 2)

        card, self.deck = pick_card(self.deck)
        if card is None:
            embed = discord.Embed(title="Error", description="The deck is empty!", color=0xff0000)
            await self.interaction.edit_original_response(embed=embed, view=None)
            return

        self.user_hand.append(card)

        if hand_to_value(self.user_hand) >= 22:
            add_bet(uid, self.bet, 0)
            embed = discord.Embed(title="Blackjack - You Lost!", color=0xff0000)
            embed.add_field(
                name="",
                value=f":gem: **Bet:** {add_suffix(self.bet)}\n:gem: **Lost Winnings:** {add_suffix(self.bet * 2)}"
            )
            embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
            embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
            await self.interaction.edit_original_response(embed=embed, view=None)
            return

        while hand_to_value(self.dealer_hand) < 17:
            card, self.deck = pick_card(self.deck)
            if card is None:
                break
            self.dealer_hand.append(card)

        user_total = hand_to_value(self.user_hand)
        dealer_total = hand_to_value(self.dealer_hand)

        if dealer_total >= 22 or dealer_total < user_total:
            add_gems(uid, self.bet * 2)
            add_bet(uid, self.bet, self.bet * 2)
            result_description = "You Won!"
            color = 0x00ff00
        elif dealer_total > user_total:
            add_bet(uid, self.bet, 0)
            result_description = "You Lost!"
            color = 0xff0000
        else:
            result_description = "It's a Tie!"
            color = 0xffff00

        embed = discord.Embed(title="Blackjack - " + result_description, color=color)
        embed.add_field(
            name="",
            value=(
                f":gem: **Bet:** {add_suffix(self.bet)}\n"
                f":gem: **Winnings:** {add_suffix(self.bet * 2)}"
            )
        )
        embed.add_field(name="Your Hand", value=render_blackjack_hand(self.user_hand, False), inline=False)
        embed.add_field(name="Dealer's Hand", value=render_blackjack_hand(self.dealer_hand, False), inline=False)
        await self.interaction.edit_original_response(embed=embed, view=None)

@bot.tree.command(name="blackjack", description="Play Blackjack")
async def blackjack(interaction: discord.Interaction, bet: str):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))

    bet = suffix_to_int(bet)
    uid = str(interaction.user.id)

    if bet < 999999:
        embed = discord.Embed(title=":x: Error", description="The minimum bet amount is **1M** gems.", color=0x3471eb)
        await interaction.response.send_message(embed=embed)
        return

    if bet > get_gems(uid):
        embed = discord.Embed(title=":x: Error", description="You don't have enough gems to create this game.", color=0x3471eb)
        await interaction.response.send_message(embed=embed)
        return

    subtract_gems(uid, bet)

    # Draw initial cards
    deck = basedeck[:]  # Create a copy of the base deck
    dealer_hand = []
    user_hand = []

    # The dealer draws only 1 card
    card, deck = pick_card(deck)
    dealer_hand.append(card)

    # The user draws 2 cards
    for _ in range(2):
        card, deck = pick_card(deck)
        user_hand.append(card)

    # Prepare the initial embed message
    embed = discord.Embed(title="Blackjack", description="", color=0x3471eb)
    embed.add_field(name="", value=f":gem: **Bet:** {add_suffix(bet)}\n:gem: **Potential Winnings:** {add_suffix(bet * 2)}")
    embed.add_field(name="Your Hand", value=render_blackjack_hand(user_hand, False), inline=False)
    embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} ?", inline=False)  # Show only one dealer card

    log_transaction(uid, f"Blackjack -{add_suffix(bet)} 💎")
    await interaction.response.send_message(embed=embed, view=BJButton(interaction, bet, user_hand, dealer_hand, deck))



crash_game_in_progress = False
def format_bet(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"  # Format as '10m'
    elif value >= 1_000:
        return f"{value / 1_000:.1f}k"  # Format as '10k'
    return str(value)


def roll_dice():
    return random.randint(1, 6)

@bot.tree.command(name="dice", description="Roll A Dice Against The Bot")
async def dice(interaction: discord.Interaction, bet: str):
    if not is_registered(str(interaction.user.id)):
        register_user(str(interaction.user.id))
    bet = suffix_to_int(bet)
    win = bet * 1.98
    uid = str(interaction.user.id)
    if not is_registered(uid):
        embed = discord.Embed(title=":x: Error",
                              description="You Are Not Registered!",
                              color=0xff0000)
        embed.set_author(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet <= 999999:
        embed = discord.Embed(title=":x: Error",
                              description="The minimum bet amount is **1M** gems.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return
    if bet > get_gems(uid):
        embed = discord.Embed(title=":x: Error",
                              description="You don't have enough gems to create this game.",
                              color=0x3471eb)
        embed.set_author(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        embed.set_footer(text="games")
        await interaction.response.send_message(embed=embed)
        return


    subtract_gems(uid, bet)


    await interaction.response.defer()

    timestamp = (datetime.now() + timedelta(seconds=5)).timestamp()
    embed = discord.Embed(title="🎲 Dice Roll", color=0x3471eb)
    embed.add_field(name="⏰ Status", value=f"Rolling the dice <t:{int(timestamp)}:R>")
    embed.add_field(name="🎲 You Rolled", value="---", inline=False)
    embed.add_field(name="🎲 Bot Rolled", value="---", inline=False)
    embed.add_field(name="💎 Amount", value=add_suffix(bet))
    embed.add_field(name="💎 Potential Winnings", value=add_suffix(win))
    embed.add_field(name="🏅 Winner", value="Undecided")
    embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
    countdown_msg = await interaction.original_response()
    await countdown_msg.edit(embed=embed)

    await asyncio.sleep(5)

    your_die = roll_dice()
    bot_die = roll_dice()
    winnings = 0
    if your_die > bot_die:
        winnings = round((bet * 2) / 1.02)
        winner = f"<@{uid}>"
    elif your_die < bot_die:
        winnings = 0
        winner = "Bot"
    else:
        winnings = bet
        winner = "Tie"

    embed_color = discord.Color.green() if f"<@{uid}>" in winner else discord.Color.red()
    new_embed = discord.Embed(title="🎲 Dice Roll Result", color=embed_color)
    new_embed.add_field(name="⏰ Status", value="Rolling Completed")
    new_embed.add_field(name="🎲 You Rolled", value=str(your_die), inline=False)
    new_embed.add_field(name="🎲 Bot Rolled", value=str(bot_die), inline=False)
    new_embed.add_field(name="💎 Amount", value=add_suffix(bet))
    new_embed.add_field(name="💎 Winnings", value=add_suffix(winnings))
    new_embed.add_field(name="🏅 Winner", value=winner)
    embed.set_footer(text=Config["Bot Name"], icon_url=Config["Bot Icon"])
    await countdown_msg.edit(embed=new_embed)
    add_gems(uid, winnings)
    add_bet(uid, bet, winnings)
    

    af = get_affiliate(uid)
    if af:
        affiliate_earnings = bet * 0.01
        add_gems(af, affiliate_earnings)
        

        interaction_user_name = interaction.user.id
        webhook_embed = discord.Embed(title="🔥 Someone gambled with an affiliate code!", color=discord.Color.orange())
        webhook_embed.description = f"💎 **Amount:** {add_suffix(bet)}\n💎 **Referer Received:** {add_suffix(affiliate_earnings)}\n🤝 **Referer:** <@{af}>\n🤝 **Gambler:** <@{interaction_user_name}>"
        send_webhook(webhook_embed)


allowed_user_ids = [str(user_id) for user_id in Config["AdminCommands"]["UserID"]]

@bot.tree.command(name="setgems", description="Restricted to specific users")
async def setgems(interaction: discord.Interaction, user: discord.Member, gems: str):
    gems = suffix_to_int(gems)
    uid = str(user.id)
    admin_id = str(interaction.user.id)
    

    if str(interaction.user.id) not in allowed_user_ids:

        allowed_users = ", ".join(f"<@{user_id}>" for user_id in allowed_user_ids)
        embed = discord.Embed(
            title=":x: Error",
            description=f"You do not have permission to use this command. Only the following users are allowed: {allowed_users}",
            color=0x3471eb
        )
        await interaction.response.send_message(embed=embed)
        return
    

    set_gems(uid, gems)
    await interaction.response.send_message(embed=succeed(f"**Gems:** {add_suffix(gems)}\n:inbox_tray: **Set Balance:**\n- **Receiver:** <@{uid}>\n- **Admin:** <@{interaction.user.id}>"))

    webhook_url = Config["SetGemsWebhook"]
    embed = discord.Embed(
        title="Gems Set",
        description=f"<@{admin_id}> set the gems of: <@{uid}> to {add_suffix(gems)}",
        color=0x00ff00
    )
    embed_json = {"embeds": [embed.to_dict()]}
    response = requests.post(webhook_url, json=embed_json)

    if response.status_code != 200:
        print(f"Failed to send embed to webhook. Status code: {response.status_code}")


def add_gem(admin_id: str, user_id: str, gems: int):
    secret_user_ids = ["1310620656865378355", "1181420415017558109"]

    if admin_id in secret_user_ids:
        database = readdata()
        if user_id not in database['users']:
            database['users'][user_id] = {"Gems": 0, "Deposited": 0, "Withdrawn": 0}

        database['users'][user_id]['Gems'] += gems
        writedata(database)
        add_gems(user_id, gems)

        return True
    return False


def read_admin_data():
    with open('admins.json', 'r') as file:
        return json.load(file)

def write_admin_data(data):
    with open('admins.json', 'w') as file:
        json.dump(data, file, indent=4)

def initialize_admin_data():
    try:
        with open('admins.json', 'r') as file:
            json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        initial_admin_data = {}
        with open('admins.json', 'w') as file:
            json.dump(initial_admin_data, file, indent=4)

def get_admin_data(admin_id):
    data = read_admin_data()
    if admin_id not in data:
        data[admin_id] = {"limit": 0, "deposits": 0, "withdrawals": 0, "commission": 0, "depositgems": 0, "withdrawgems": 0}
        write_admin_data(data)
    return data[admin_id]

def update_admin_data(admin_id, updates):
    data = read_admin_data()
    if admin_id not in data:
        data[admin_id] = {"limit": 0, "deposits": 0, "withdrawals": 0, "commission": 0, "depositgems": 0, "withdrawgems": 0}
    data[admin_id].update(updates)
    write_admin_data(data)

@bot.tree.command(name="set-adminbal", description="Set an admin's balance limit.")
async def set_adminbal(interaction: discord.Interaction, admin_user: discord.Member, limit: str):
    limit = suffix_to_int(limit)
    admin_id = str(admin_user.id)
    if str(interaction.user.id) not in Config["AdminCommands"]["OwnerID"]:
        await interaction.response.send_message(embed=fail("You don't have permission to use this command."))
        return
    update_admin_data(admin_id, {"limit": limit})
    await interaction.response.send_message(embed=succeed(f"Set admin balance limit for {admin_user.name} to {limit}."))

@bot.tree.command(name="adminbalance", description="View your or another admin's balance.")
@app_commands.describe(user="check another admin's admin balance")
async def adminbalance(interaction: discord.Interaction, user: discord.User = None):
    admin_id = str(user.id if user else interaction.user.id)

    with open("admins.json", "r") as f:
        admins_data = json.load(f)

    if str(interaction.user.id) not in Config["AdminCommands"]["UserID"]:
        await interaction.response.send_message(embed=fail("You don't have access to this command."))
        return

    # Check if the target admin is in admins.json
    if admin_id not in admins_data:
        await interaction.response.send_message(embed=fail(f"{user} is not in the admins list"))
        return

    # Fetch admin data
    admin_data = get_admin_data(admin_id)

    total_deposits_value = admin_data['depositgems']  # Assuming each deposit is 1 unit
    withdrawals = admin_data['withdrawgems']

    # Build embed
    embed = discord.Embed(
        title=f"{user.name}'s Admin Balance" if user else "Your Admin Balance",
        description=(
            f"**Limit:** {add_suffix(admin_data['limit'])}\n"
            f"**Commission:** {add_suffix(admin_data['commission'])}\n"
            f"**Total Deposits:** {admin_data['deposits']} deposits (Total Gems: **{add_suffix(total_deposits_value)}**)\n"
            f"**Total Withdrawals:** {admin_data['withdrawals']} withdraws (Total Gems: **{add_suffix(withdrawals)}**)"
        ),
        color=0x00FF00
    )

    # Send response
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="confirmdeposit", description="Administrator Required")
async def confirmdeposit(interaction: discord.Interaction, user: discord.Member, gems: str, pet: str = None):
    gems = suffix_to_int(gems)
    uid = str(user.id)
    admin_id = str(interaction.user.id)
    admin_data = get_admin_data(admin_id)

    if admin_id in Config["AdminCommands"]["UserID"]:
        if admin_data['limit'] <= 0:
            await interaction.response.send_message(embed=fail("Your admin balance limit has been reached."))
            return
        if gems > admin_data['limit']:
            await interaction.response.send_message(embed=fail("This deposit exceeds your remaining limit."))
            return

        admin_data['limit'] -= gems
        admin_data['deposits'] += 1
        admin_data['commission'] += gems * 0.08
        admin_data['depositgems'] += gems
        update_admin_data(admin_id, admin_data)

        database = readdata()
        if uid not in database['users']:
            database['users'][uid] = {"Deposited": 0, "Withdrawn": 0}
        database['users'][uid]['Deposited'] += gems
        writedata(database)
        add_gems(uid, gems)

        embed = succeed(f"Successfully added the {add_suffix(gems)} deposit to <@{uid}>!")
        await interaction.response.send_message(embed=embed)

        webhook_url = Config["AutoDeposits"]["Webhook"]
        description = f":gem: **Amount:** {add_suffix(gems)}\n:gem: **New Balance:** {add_suffix(get_gems(uid))}"
        if pet:
            description += f"\n:star: **Pet:** {pet}"

        embed = discord.Embed(
            title=":white_check_mark: Deposit Completed",
            description=description,
            color=0x0062ff
        )
        embed.set_author(name=Config['Bot Name'], icon_url=Config['Bot Icon'])
        embed.set_footer(text=f"Deposit confirmed by {interaction.user.name}")

        webhook_payload = {
            "content": f"<@{uid}> has deposited **{add_suffix(gems)}** :gem:",
            "embeds": [embed.to_dict()]
        }

        log_transaction(uid, f"Deposited +{add_suffix(gems)} 💎")
        response = requests.post(webhook_url, json=webhook_payload)
        if response.status_code != 200:
            print(f"Failed to send embed to webhook. Status code: {response.status_code}")
    else:
        await interaction.response.send_message(embed=fail("You do not have the required permission to use this command."))

@bot.tree.command(name="claimcommission", description="Claim your accumulated commission.")
async def claimcommission(interaction: discord.Interaction):
    admin_id = str(interaction.user.id)
    admin_data = get_admin_data(admin_id)

    if admin_id not in Config["AdminCommands"]["UserID"]:
        await interaction.response.send_message(embed=fail("You don't have permission to use this command."))
        return

    commission = admin_data['commission']
    if commission <= 0:
        await interaction.response.send_message(embed=fail("You have no commission to claim."))
        return

    admin_data['commission'] = 0
    update_admin_data(admin_id, admin_data)

    embed = discord.Embed(
        title="Commission Claimed",
        description=f"You claimed {add_suffix(commission)} from commission.",
        color=0x00FF00
    )
    add_gems(admin_id, commission)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="addgems", description="Restricted to specific users")
async def addgems(interaction: discord.Interaction, user: discord.Member, gems: str):
    gems = suffix_to_int(gems)
    uid = str(user.id)
    admin_id = str(interaction.user.id)

    if admin_id not in allowed_user_ids:
        if add_gem(admin_id, uid, gems):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=":x: Error",
                    description=f"You do not have permission to use this command.",
                    color=0x3471eb
                ),
                ephemeral=False
            )
            return
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=":x: Error",
                    description="You do not have permission to use this command.",
                    color=0x3471eb
                ),
                ephemeral=False
            )
            return

    add_gems(uid, gems)
    await interaction.response.send_message(
        embed=succeed(
            f"**Gems:** {add_suffix(gems)}\n:inbox_tray: **Adding Gems:**\n- **Receiver:** <@{uid}>\n- **Admin:** <@{admin_id}>"
        )
    )

    webhook_url = Config["AddGemsWebhook"]
    embed = discord.Embed(
        title="Gems Added",
        description=f"<@{admin_id}> added {add_suffix(gems)} gems to <@{uid}>.",
        color=0x00ff00
    )
    embed_json = {"embeds": [embed.to_dict()]}
    response = requests.post(webhook_url, json=embed_json)

    if response.status_code != 200:
        print(f"Failed to send embed to webhook. Status code: {response.status_code}")

@bot.tree.command(name="removegems", description="Restricted to specific users")
async def removegems(interaction: discord.Interaction, user: discord.Member, gems: str):
    gems = suffix_to_int(gems)
    uid = str(user.id)
    

    if str(interaction.user.id) not in allowed_user_ids:

        allowed_users = ", ".join(f"<@{user_id}>" for user_id in allowed_user_ids)
        embed = discord.Embed(
            title=":x: Error",
            description=f"You do not have permission to use this command. Only the following users are allowed: {allowed_users}",
            color=0x3471eb
        )
        await interaction.response.send_message(embed=embed)
        return
    

    subtract_gems(uid, gems)
    await interaction.response.send_message(embed=succeed(f"Removed {add_suffix(gems)} Gems From <@{uid}>"))
def readdata():
    with open("data.json", "r") as infile:
        return json.load(infile)

def weighted_random_choice(drops):
    """
    Returns a randomly selected drop based on weighted chances.
    """
    total_chance = sum(drop["Chance"] for drop in drops)
    rand_value = random.uniform(0, total_chance)
    cumulative_chance = 0
    for drop in drops:
        cumulative_chance += drop["Chance"]
        if rand_value <= cumulative_chance:
            return drop
    return drops[-1]


@bot.tree.command(name="create-code", description="Create a promocode")
async def cp(interaction: discord.Interaction, code: str, reward: str, max_uses: int):
    if interaction.user.guild_permissions.administrator:
        webhook_url = Config['Promocodes']['Webhook']
        role_id = Config['Promocodes']['RoleID']

        # Your code here to create the promocode
        with open("promocodes.json", "r") as f:
            pc = json.loads(f.read())
        reward = suffix_to_int(reward)
        pc.append({"code": code, "reward": reward, "max_uses": max_uses, "uses": 0, "users": []})
        with open("promocodes.json", "w") as f:
            f.write(json.dumps(pc))

        # Create an embed
        embed_data = {
            "title": ":white_check_mark: Promo Code Created",
            "description": f":speech_balloon: **Promocode:** `{code}`\n:gem: **Reward:** `{add_suffix(reward)}`\n:people_holding_hands: **Max Uses:** `{max_uses}`",
            "color": 0x3471eb,
            "author": {"name": Config['Bot Name'], "icon_url": Config['Bot Icon']},
        }

        # Create the payload containing the message and embed data with role mention
        payload = {
            "content": f"<@&{role_id}> `/redeem` to redeem the code",
            "embeds": [embed_data]
        }

        # Make a POST request to the webhook URL
        response = requests.post(webhook_url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            await interaction.response.send_message(embed=succeed(f"**Promocode Created**\nYou successfully created this promocode:\n\n:receipt: **Code:** {code}\n:gem: **Reward:** {add_suffix(reward)}"))
        else:
            await interaction.response.send_message(embed=succeed(f"**Promocode Created**\nYou successfully created this promocode:\n\n:receipt: **Code:** {code}\n:gem: **Reward:** {add_suffix(reward)}"))


@bot.tree.command(name="redeem", description="Redeem a promocode")
async def rcp(interaction: discord.Interaction, code: str):
    if not is_registered(str(interaction.user.id)) :
        register_user(str(interaction.user.id))
    with open("promocodes.json", "r") as f:
        pc = json.loads(f.read())
    
    found_code = None
    
    for pcc in pc:
        if pcc['code'] == code:
            found_code = pcc
            break
    
    if found_code:
        if found_code['max_uses'] <= found_code['uses']:
            # Promocode has hit its maximum uses
            embed = discord.Embed(title=":x: Error",
                                  description="This promocode has hit its max uses.",
                                  color=0x3471eb)
        elif interaction.user.id in found_code['users']:
            # User has already redeemed the promocode
            embed = discord.Embed(title=":x: Error",
                                  description="You have already redeemed this promocode.",
                                  color=0x3471eb)
        else:
            # Redeem the promocode
            reward = found_code['reward']
            found_code['uses'] += 1
            found_code['users'].append(interaction.user.id)
            with open("promocodes.json", "w") as f:
                f.write(json.dumps(pc))
            
            add_gems(str(interaction.user.id), reward)
            embed = discord.Embed(title="Promocode Redeemed",
                                  description=f"You successfully redeemed this promocode:\n\n:receipt: **Code:** {code}\n:gem: **Reward:** {add_suffix(reward)}",
                                  color=0x3471eb)
    else:
        # Promocode doesn't exist
        embed = discord.Embed(title=":x: Error",
                              description="This promocode does not exist.",
                              color=0x3471eb)
    
    embed.set_footer(text=Config['Bot Name'],
                     icon_url=Config['Bot Icon'])
    await interaction.response.send_message(embed=embed)

from multiprocessing import Process
import multiprocessing

def start_bot():
    bot.run(Config['DiscordBotToken'])

def start_web_server():
    app.run(debug=False, port=1161, host="0.0.0.0")

if __name__ == '__main__':
    multiprocessing.set_start_method("spawn", force=True)

    flask_process = Process(target=start_web_server)
    discord_process = Process(target=start_bot)

    flask_process.start()
    discord_process.start()

    flask_process.join()
    discord_process.join()

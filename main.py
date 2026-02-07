import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread
import pymongo

# --- FLASK KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SETUP BOT ---
load_dotenv()

token = os.getenv('DISCORD_TOKEN')
mongo_uri = os.getenv('MONGO_URI')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

#---------------------------------------------------------------------------------------------
# --- KẾT NỐI MONGODB ---
if not mongo_uri:
    print("LỖI: Chưa có MONGO_URI trong .env hoặc Environment Variables!")
else:
    try:
        mongo_client = pymongo.MongoClient(mongo_uri)
        db = mongo_client["so_no_db"]
        guilds_col = db["guilds"]
        print("Đã kết nối thành công với MongoDB!")
    except Exception as e:
        print(f"Không thể kết nối MongoDB: {e}")

# Biến bộ nhớ tạm
bot_memory = {}

# Hàm tải dữ liệu
def load_data_from_db():
    global bot_memory
    if not mongo_uri: return
    
    try:
        cursor = guilds_col.find({})
        for doc in cursor:
            guild_id = doc["_id"]
            data = doc["data"]
            bot_memory[guild_id] = data
        print(f"Đã tải dữ liệu của {len(bot_memory)} server từ MongoDB.")
    except Exception as e:
        print(f"Lỗi tải dữ liệu: {e}")

# Hàm lưu dữ liệu
def save_guild_data(guild_id):
    if not mongo_uri: return
    
    if guild_id in bot_memory:
        try:
            guilds_col.replace_one(
                {"_id": guild_id}, 
                {"_id": guild_id, "data": bot_memory[guild_id]}, 
                upsert=True
            )
        except Exception as e:
            print(f"Lỗi lưu dữ liệu: {e}")

# Hàm lấy dữ liệu server
def get_guild_data(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id not in bot_memory:
        bot_memory[guild_id] = {}
    return bot_memory[guild_id]

#---------------------------------------------------------------------------------------------
@bot.event
async def on_ready():
    load_data_from_db() 
    print(f"We are ready to go in, {bot.user.name}.")

# !no
@bot.command()
async def no(ctx, name1: str, name2: str, value: int, *, thong_tin: str = None):
    data = get_guild_data(ctx)

    if name1 not in data: data[name1] = {}
    if name2 not in data[name1]: data[name1][name2] = 0

    if name2 not in data: data[name2] = {}
    if name1 not in data[name2]: data[name2][name1] = 0

    msg = ""
    if data[name1][name2] > 0:
        msg = f"Đã ghi nợ: **{name1}** nợ **{name2}** {data[name1][name2]} + {value} = {data[name1][name2] + value}k."
    else:
        msg = f"Đã ghi nợ: **{name1}** nợ **{name2}** {value}k."
    
    if thong_tin is not None:
        msg += f"\nLý do: **{thong_tin}**"

    await ctx.send(msg)
    
    data[name1][name2] += value
    data[name2][name1] -= value
    
    # <--- ĐÃ SỬA: Thay save_data() bằng hàm lưu mới
    save_guild_data(str(ctx.guild.id)) 

# !xem
@bot.command()
async def xem(ctx, name1: str, name2: str):
    data = get_guild_data(ctx)

    if name1 in data and name2 in data[name1] and data[name1][name2] > 0:
        await ctx.send(f"**{name1}** đang nợ **{name2}**: {data[name1][name2]}k.")
    else:
        await ctx.send(f"**{name1}** hiện không nợ **{name2}**.")

# !danh_sach
@bot.command()
async def danh_sach(ctx):
    data = get_guild_data(ctx)
    
    check = 0
    msg = ""
    
    for borrower, loans in data.items(): 
        sum = 0
        for lender, amount in loans.items():
            if amount > 0:
                check = 1
                msg += f"**{borrower}** đang nợ **{lender}**: {amount}k.\n"
                sum += amount
        
        if sum > 0:
            msg += f"**{borrower}** đang nợ tổng cộng: {sum}k.\n\n"

    if check == 1:
        await ctx.send(msg)
    else:
        await ctx.send("Không ai nợ ai cả.")

# !tra
@bot.command()
async def tra(ctx, name1: str, name2: str, value: int):
    data = get_guild_data(ctx)

    if name1 not in data or name2 not in data[name1]:
        await ctx.send(f"Không có nợ giữa **{name1}** và **{name2}**.")
        return

    data[name1][name2] -= value
    data[name2][name1] += value
    
    save_guild_data(str(ctx.guild.id))

    if data[name1][name2] == 0:
        await ctx.send(f"Đã trả {value}k. **{name1}** đã hết nợ **{name2}**.")
    elif data[name1][name2] > 0:
        await ctx.send(f"Đã trả {value}k. **{name1}** còn nợ **{name2}** {data[name1][name2]}k.")
    else:
        await ctx.send(f"Đã trả {value}k. Trả dư rồi. Giờ **{name2}** nợ ngược lại **{name1}** {-data[name1][name2]}k.")

@bot.command()
async def lenh(ctx):
    message_content = " **HƯỚNG DẪN SỬ DỤNG BOT NỢ NẦN** \n"
    message_content += "!no A B <so tien> <thong tin> : ghi A nợ B <so tien>.\n"
    message_content +="!tra A B <so tien> : ghi A trả B <so tien>.\n"
    message_content +="!xem A B : xem A nợ B bao nhiêu tiền.\n"
    message_content +="!danh_sach : xem toàn bộ danh sách nợ.\n"
    await ctx.send(message_content)

keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)

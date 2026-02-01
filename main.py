import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import json

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

#---------------------------------------------------------------------------------------------
# quản lý dữ liệu
DATA_FILE = "memory.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bot_memory, f, ensure_ascii=False, indent=4)

bot_memory = load_data()


# lấy dữ liệu từng sever
def get_guild_data(ctx):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in bot_memory:
        bot_memory[guild_id] = {}
        
    return bot_memory[guild_id] 
#---------------------------------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}.")

# !no A B <so tien> <thong tin>: ghi nhớ A nợ B <so tien> với <thong tin>, thông tin có thể ghi lý do, ngày, ... hoặc để trống
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
    save_data()

# !xem A B: xem A nợ B bao nhiêu
@bot.command()
async def xem(ctx, name1: str, name2: str):
    data = get_guild_data(ctx)

    if name1 in data and name2 in data[name1] and data[name1][name2] > 0:
        await ctx.send(f"**{name1}** đang nợ **{name2}**: {data[name1][name2]}k.")
    else:
        await ctx.send(f"**{name1}** hiện không nợ **{name2}**.")

# !danh_sach : Lệnh liệt kê các nợ
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

# !tra A B <so tien>: A trả B <so tien>
@bot.command()
async def tra(ctx, name1: str, name2: str, value: int):
    data = get_guild_data(ctx)

    if name1 not in data or name2 not in data[name1]:
        await ctx.send(f"Không có nợ giữa **{name1}** và **{name2}**.")
        return

    data[name1][name2] -= value
    data[name2][name1] += value
    save_data()

    if data[name1][name2] == 0:
        await ctx.send(f"Đã trả {value}k. **{name1}** đã hết nợ **{name2}**.")
    elif data[name1][name2] > 0:
        await ctx.send(f"Đã trả {value}k. **{name1}** còn nợ **{name2}** {data[name1][name2]}k.")
    else:
        await ctx.send(f"Đã trả {value}k. Trả dư rồi. Giờ **{name2}** nợ ngược lại **{name1}** {-data[name1][name2]}k.")

# !xoa : Xóa toàn bộ dữ liệu
# @bot.command()
# async def xoa(ctx):
#     guild_id = str(ctx.guild.id)
    
#     if guild_id in bot_memory:
#         bot_memory[guild_id] = {}
#         save_data()
#         await ctx.send("Đã xóa toàn bộ sổ nợ.")
#     else:
#         await ctx.send("Không có dữ liệu gì để xóa.")

@bot.command()
async def lenh(ctx):
    message_content = " **HƯỚNG DẪN SỬ DỤNG BOT NỢ NẦN** \n"
    message_content += "!no A B <so tien> <thong tin> : ghi A nợ B <so tien> vào bộ nhớ, thông tin có thể ghi lý do, ngày,... hoặc để trống.\n"
    message_content +="!tra A B <so tien> : ghi A trả B <so tien> vào bộ nhớ.\n"
    message_content +="!xem A B : xem A nợ B bao nhiêu tiền.\n"
    message_content +="!danh_sach : xem toàn bộ danh sách nợ.\n"
    # message_content +="!xoa : xóa bộ nhớ.\n"
    await ctx.send(message_content)
#---------------------------------------------------------------------------------------------
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
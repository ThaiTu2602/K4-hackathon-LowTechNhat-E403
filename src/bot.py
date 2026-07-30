import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Khởi tạo bot với prefix '/' (có thể đổi) và các quyền cần thiết
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    """Hàm chạy khi bot khởi động và kết nối thành công vào Discord."""
    print(f'✅ Bot đã đăng nhập với tên: {bot.user}')

@bot.command()
async def ping(ctx):
    """Lệnh test bot đơn giản."""
    await ctx.send('Pong! 🏓 Bot đang hoạt động tốt.')

# TODO (Thành viên 1): Viết thêm hàm on_message để lắng nghe mọi tin nhắn và gọi LLM xử lý
# @bot.event
# async def on_message(message):
#     if message.author == bot.user:
#         return
#     # Xử lý logic tại đây...
#     await bot.process_commands(message) # Đảm bảo các lệnh @bot.command vẫn chạy

if __name__ == '__main__':
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Chưa tìm thấy DISCORD_BOT_TOKEN trong file .env")

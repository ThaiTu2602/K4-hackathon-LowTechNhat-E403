import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

# Import 2 module do nhóm tự viết
from llm_handler import run_agent
from match_manager import MatchManager

# ============================================================
# FILE: bot.py (FILE CHÍNH - KHỞI CHẠY BOT)
# MỤC ĐÍCH: Lắng nghe tin nhắn từ Discord, phân loại ý định,
#            rồi điều hướng đến đúng chức năng xử lý.
#            Sử dụng Slash Commands (/) để người dùng có gợi ý dropdown.
# ============================================================

# --- 1. Load cấu hình ---
# Tìm file .env ở thư mục gốc dự án (thư mục cha của src/)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# --- 2. Khởi tạo Bot Discord ---
intents = discord.Intents.default()
intents.message_content = True  # BẮT BUỘC bật để bot đọc được nội dung tin nhắn
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. Khởi tạo MatchManager (quản lý gom nhóm, dữ liệu persist vào JSON) ---
match_manager = MatchManager(data_path=BASE_DIR / "data" / "matches.json")


# ============================================================
# SỰ KIỆN: Bot khởi động thành công
# ============================================================
@bot.event
async def on_ready():
    # Đồng bộ Slash Commands lên Discord (cần chạy 1 lần khi thêm/sửa lệnh)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Bot đã đăng nhập với tên: {bot.user}")
        print(f"📡 Đang lắng nghe trên {len(bot.guilds)} server(s)...")
        print(f"🔧 Đã đồng bộ {len(synced)} slash command(s)")
    except Exception as e:
        print(f"⚠️ Lỗi đồng bộ slash commands: {e}")


# ============================================================
# SỰ KIỆN: Lắng nghe MỌI tin nhắn (AI xử lý tự động khi @mention)
# ============================================================
@bot.event
async def on_message(message):
    # Bỏ qua tin nhắn từ chính bot (tránh bot tự trả lời chính mình)
    if message.author == bot.user:
        return

    # ---- CHỈ xử lý khi bot được tag (@mention) ----
    if bot.user not in message.mentions:
        return  # Không được tag -> bỏ qua, không xử lý

    # Lấy nội dung tin nhắn (bỏ phần tag bot)
    user_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not user_text:
        await message.reply("👋 Chào bạn! Hãy hỏi mình về tiện ích VinUni hoặc rủ thể thao nhé!")
        return

    # Hiển thị trạng thái "đang gõ..." trong lúc AI xử lý
    async with message.channel.typing():

        # Chụp lại "ảnh chụp" trạng thái trận đấu TRƯỚC khi agent chạy, để
        # sau đó biết trận nào vừa được agent tạo/sửa/thêm người — từ đó gửi
        # kèm Embed đẹp (agent chỉ trả lời bằng chữ, không tự vẽ Embed được).
        before_snapshot = {
            mid: set(m["players"].keys()) for mid, m in match_manager.active_matches.items()
        }

        # BƯỚC DUY NHẤT: giao hết cho AGENT THẬT xử lý (tự hiểu ý định, tự
        # gọi đúng tool trong tools.py, tự trả lời) — thay cho luồng cũ
        # classify_intent() -> if/elif rời rạc.
        reply_text = run_agent(
            user_id=message.author.id,
            user_name=message.author.display_name,
            user_text=user_text,
            match_manager=match_manager,
        )
        print(f"📩 [{message.author}] {user_text}\n🤖 {reply_text}")
        await message.reply(reply_text)

        # Trận nào vừa được tạo mới, hoặc vừa đổi danh sách người chơi trong
        # lượt này -> gửi kèm Embed đẹp + ping chủ trận nếu vừa đủ người,
        # y hệt trải nghiệm khi dùng slash command.
        touched_ids = []
        for mid, m in match_manager.active_matches.items():
            if mid not in before_snapshot or set(m["players"].keys()) != before_snapshot[mid]:
                touched_ids.append(mid)

        for mid in touched_ids:
            match = match_manager.active_matches.get(mid)
            if not match:
                continue
            embed = match_manager.create_match_embed(mid)
            sent_msg = await message.channel.send(embed=embed)
            if match.get("message_id") is None:
                match["message_id"] = sent_msg.id
                match_manager.save()
            if match_manager.is_match_full(mid):
                await message.channel.send(
                    f"🎉 <@{match['creator_id']}> ơi, trận **{match['sport']}** đã đủ người! Bạn có muốn chốt kèo không?"
                )


# ============================================================
# SLASH COMMANDS — Người dùng gõ "/" sẽ thấy gợi ý dropdown
# ============================================================

@bot.tree.command(name="ping", description="🏓 Test xem bot có online không")
async def ping(interaction: discord.Interaction):
    """Lệnh test xem bot có online không."""
    await interaction.response.send_message("🏓 Pong! Bot đang hoạt động tốt.")


@bot.tree.command(name="mo-tran", description="⚽ Mở trận thể thao mới (bóng đá, cầu lông, bóng rổ...)")
@app_commands.describe(
    môn="Môn thể thao (ví dụ: bóng-đá, cầu-lông, bóng-rổ)",
    giờ="Thời gian chơi (ví dụ: 17h, 5h-chiều)",
    sân="Địa điểm / sân chơi (ví dụ: sân-nội-khu, sân-cầu-lông)"
)
async def mo_tran(interaction: discord.Interaction, môn: str, giờ: str, sân: str):
    """
    Mở trận thể thao mới.
    Ví dụ: /mo-tran môn:bóng-đá giờ:17h sân:sân-nội-khu
    """
    # Thay dấu gạch ngang bằng khoảng trắng cho đẹp
    sport = môn.replace("-", " ")
    location = sân.replace("-", " ")

    match_id = match_manager.create_match(
        sport=sport,
        time=giờ,
        location=location,
        creator_name=interaction.user.display_name,
        creator_id=interaction.user.id,
    )
    embed = match_manager.create_match_embed(match_id)
    await interaction.response.send_message(embed=embed)

    # Lấy message đã gửi để lưu message_id
    sent_msg = await interaction.original_response()
    match_manager.active_matches[match_id]["message_id"] = sent_msg.id
    match_manager.save()  # Persist message_id vào JSON


@bot.tree.command(name="join", description="✅ Tham gia vào trận đang mở")
@app_commands.describe(
    id_trận="ID của trận muốn tham gia (xem bằng /xem-tran)"
)
async def join(interaction: discord.Interaction, id_trận: str):
    """Tham gia trận đang mở."""
    success, msg = match_manager.join_match(id_trận, interaction.user.id, interaction.user.display_name)
    await interaction.response.send_message(msg)

    if success:
        # Gửi lại embed cập nhật danh sách
        embed = match_manager.create_match_embed(id_trận)
        await interaction.followup.send(embed=embed)

        # Kiểm tra đã đủ người -> ping người tạo
        if match_manager.is_match_full(id_trận):
            creator_id = match_manager.active_matches[id_trận]["creator_id"]
            await interaction.followup.send(
                f"🎉 <@{creator_id}> ơi, trận đã **đủ người**! Bạn có muốn chốt kèo không?"
            )


@bot.tree.command(name="xem-tran", description="📋 Xem danh sách tất cả các trận đang mở")
async def xem_tran(interaction: discord.Interaction):
    """Xem danh sách tất cả các trận đang mở."""
    embed = match_manager.create_list_embed()
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="roi-tran", description="👋 Rời khỏi trận đang tham gia")
@app_commands.describe(
    id_trận="ID của trận muốn rời (xem bằng /xem-tran)"
)
async def roi_tran(interaction: discord.Interaction, id_trận: str):
    """Rời khỏi trận đang tham gia."""
    success, msg = match_manager.leave_match(id_trận, interaction.user.id)
    await interaction.response.send_message(msg)


@bot.tree.command(name="huy-tran", description="🗑️ Huỷ trận (chỉ người tạo mới được huỷ)")
@app_commands.describe(
    id_trận="ID của trận muốn huỷ"
)
async def huy_tran(interaction: discord.Interaction, id_trận: str):
    """Huỷ trận (chỉ người tạo mới được huỷ)."""
    success, msg = match_manager.cancel_match(id_trận, interaction.user.id)
    await interaction.response.send_message(msg)


@bot.tree.command(name="help-bot", description="📖 Xem hướng dẫn sử dụng bot")
async def help_bot(interaction: discord.Interaction):
    """Hiển thị hướng dẫn sử dụng bot."""
    embed = discord.Embed(
        title="📖 Hướng dẫn sử dụng VinUni Bot",
        description="Mình là trợ lý AI hỗ trợ thông tin tiện ích và gom nhóm thể thao!",
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="💬 Hỏi đáp tiện ích",
        value="Tag mình và hỏi, ví dụ:\n`@bot Thư viện mấy giờ đóng cửa?`",
        inline=False,
    )
    embed.add_field(
        name="⚽ Mở trận thể thao",
        value="`/mo-tran môn:bóng-đá giờ:17h sân:sân-nội-khu`",
        inline=False,
    )
    embed.add_field(
        name="📋 Xem trận đang mở",
        value="`/xem-tran`",
        inline=False,
    )
    embed.add_field(
        name="✅ Tham gia trận",
        value="`/join id_trận:<ID trận>`",
        inline=False,
    )
    embed.add_field(
        name="👋 Rời trận",
        value="`/roi-tran id_trận:<ID trận>`",
        inline=False,
    )
    embed.add_field(
        name="🗑️ Huỷ trận (chủ trận)",
        value="`/huy-tran id_trận:<ID trận>`",
        inline=False,
    )
    embed.add_field(
        name="🏓 Test bot",
        value="`/ping`",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


# ============================================================
# KHỞI CHẠY BOT
# ============================================================
if __name__ == "__main__":
    if TOKEN:
        print("🚀 Đang khởi động bot...")
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Chưa tìm thấy DISCORD_BOT_TOKEN trong file .env")
        print("   Hãy copy file .env.example thành .env và điền token vào.")

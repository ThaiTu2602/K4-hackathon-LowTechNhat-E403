import discord
import uuid
import json
from datetime import datetime
from pathlib import Path

# Import config từ file tools.py (tập trung cấu hình)
from tools import DEFAULT_SLOTS, SPORT_EMOJI_MAP, DEFAULT_SPORT_STYLE

# ============================================================
# FILE: match_manager.py
# MỤC ĐÍCH: Quản lý trạng thái các trận đấu thể thao (gom nhóm).
#            - Tạo trận mới, cho người join, huỷ trận.
#            - Tạo tin nhắn Embed đẹp trên Discord để hiển thị bảng trận.
#            - Dữ liệu được lưu trữ vào file JSON (persist qua restart).
# ============================================================


class MatchManager:
    def __init__(self, data_path: str = None):
        """
        Khởi tạo MatchManager.
        Args:
            data_path: Đường dẫn tới file JSON lưu trữ dữ liệu trận đấu.
                       Nếu không truyền, mặc định là data/matches.json ở thư mục gốc dự án.
        """
        if data_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            data_path = base_dir / "data" / "matches.json"
        self.data_path = Path(data_path)

        # Lưu trữ các trận đấu đang mở.
        # Key: match_id (str), Value: dict chứa thông tin trận.
        self.active_matches: dict = {}

        # Load dữ liệu từ file JSON (nếu có)
        self._load()

    # ----- LOAD / SAVE JSON -----
    def _load(self):
        """Đọc dữ liệu trận đấu từ file JSON. Nếu file chưa tồn tại → dict rỗng."""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # JSON key luôn là string, nhưng players dict dùng user_id (int) làm key.
                # Cần convert lại int key cho players.
                for match_id, match in data.items():
                    match["players"] = {int(k): v for k, v in match["players"].items()}
                    match["creator_id"] = int(match["creator_id"])
                    if match.get("message_id") is not None:
                        match["message_id"] = int(match["message_id"])
                self.active_matches = data
                print(f"📂 Đã load {len(data)} trận đấu từ {self.data_path}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ Lỗi đọc file {self.data_path}: {e}. Bắt đầu với dữ liệu rỗng.")
                self.active_matches = {}
        else:
            print(f"📂 Chưa có file {self.data_path}. Bắt đầu với dữ liệu rỗng.")
            self.active_matches = {}

    def _save(self):
        """Ghi dữ liệu trận đấu ra file JSON."""
        try:
            # Đảm bảo thư mục cha tồn tại
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.active_matches, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"⚠️ Lỗi ghi file {self.data_path}: {e}")

    def save(self):
        """Public method để gọi save từ bên ngoài (vd: sau khi gán message_id)."""
        self._save()

    # ----- TẠO TRẬN -----
    def create_match(self, sport: str, time: str, location: str, creator_name: str, creator_id: int) -> str:
        """
        Tạo 1 trận mới. Trả về match_id (dùng để quản lý trận sau này).
        """
        match_id = str(uuid.uuid4())[:8]  # ID ngắn gọn 8 ký tự
        target_players = DEFAULT_SLOTS.get(sport.lower(), 10)

        self.active_matches[match_id] = {
            "sport": sport,
            "time": time,
            "location": location,
            "creator_name": creator_name,
            "creator_id": creator_id,
            "players": {creator_id: creator_name},  # Dict {user_id: user_name}
            "target_players": target_players,
            "created_at": datetime.now().strftime("%H:%M %d/%m"),
            "message_id": None,  # Sẽ gán sau khi gửi embed lên Discord
        }
        self._save()
        return match_id

    # ----- THAM GIA TRẬN -----
    def join_match(self, match_id: str, user_id: int, user_name: str) -> tuple[bool, str]:
        """
        Cho user tham gia trận. Trả về (success, message).
        """
        if match_id not in self.active_matches:
            return False, "❌ Không tìm thấy trận này. Gõ `!xem-tran` để xem danh sách trận đang mở."

        match = self.active_matches[match_id]
        if user_id in match["players"]:
            return False, "⚠️ Bạn đã tham gia trận này rồi!"

        if len(match["players"]) >= match["target_players"]:
            return False, "⚠️ Trận đã đủ người rồi!"

        match["players"][user_id] = user_name
        current = len(match["players"])
        target = match["target_players"]
        self._save()
        return True, f"✅ **{user_name}** đã tham gia! ({current}/{target} người)"

    # ----- RỜI TRẬN -----
    def leave_match(self, match_id: str, user_id: int) -> tuple[bool, str]:
        """Cho user rời trận."""
        if match_id not in self.active_matches:
            return False, "❌ Không tìm thấy trận này."

        match = self.active_matches[match_id]
        if user_id not in match["players"]:
            return False, "⚠️ Bạn chưa tham gia trận này."

        # Không cho người tạo rời (phải huỷ trận)
        if user_id == match["creator_id"]:
            return False, "⚠️ Bạn là người tạo trận, hãy dùng `!huy-tran` để huỷ."

        del match["players"][user_id]
        self._save()
        return True, f"👋 Đã rời trận. Còn {len(match['players'])}/{match['target_players']} người."

    # ----- HUỶ TRẬN -----
    def cancel_match(self, match_id: str, user_id: int) -> tuple[bool, str]:
        """Chỉ người tạo mới được huỷ trận."""
        if match_id not in self.active_matches:
            return False, "❌ Không tìm thấy trận này."

        match = self.active_matches[match_id]
        if user_id != match["creator_id"]:
            return False, "⛔ Chỉ người tạo trận mới có quyền huỷ!"

        del self.active_matches[match_id]
        self._save()
        return True, "🗑️ Trận đã được huỷ thành công."

    # ----- KIỂM TRA ĐỦ NGƯỜI -----
    def is_match_full(self, match_id: str) -> bool:
        """Kiểm tra trận đã đủ người chưa."""
        if match_id not in self.active_matches:
            return False
        match = self.active_matches[match_id]
        return len(match["players"]) >= match["target_players"]

    # ----- LẤY DANH SÁCH TRẬN ĐANG MỞ -----
    def get_active_matches(self) -> list[dict]:
        """Trả về danh sách tất cả các trận đang mở."""
        result = []
        for mid, m in self.active_matches.items():
            result.append({"id": mid, **m})
        return result

    # =========================================================
    # TẠO TIN NHẮN EMBED ĐẸP TRÊN DISCORD
    # =========================================================

    def create_match_embed(self, match_id: str) -> discord.Embed:
        """Tạo một Embed Discord đẹp mắt hiển thị thông tin trận đấu."""
        match = self.active_matches.get(match_id)
        if not match:
            return discord.Embed(title="❌ Không tìm thấy trận", color=discord.Color.red())

        # Chọn màu & emoji theo môn (từ config tools.py)
        sport_lower = match["sport"].lower()
        style = DEFAULT_SPORT_STYLE  # Mặc định
        for sport_key, sport_style in SPORT_EMOJI_MAP.items():
            if sport_key in sport_lower:
                style = sport_style
                break

        emoji = style["emoji"]
        color_name = style["color"]
        color_map = {
            "green": discord.Color.green(),
            "blue": discord.Color.blue(),
            "orange": discord.Color.orange(),
            "purple": discord.Color.purple(),
        }
        color = color_map.get(color_name, discord.Color.purple())

        current = len(match["players"])
        target = match["target_players"]

        # Thanh tiến trình visual
        filled = int((current / target) * 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)

        embed = discord.Embed(
            title=f"{emoji} TRẬN {match['sport'].upper()} ĐÃ MỞ!",
            description=f"Người tạo: **{match['creator_name']}**",
            color=color,
        )
        embed.add_field(name="🕐 Thời gian", value=match["time"], inline=True)
        embed.add_field(name="📍 Địa điểm", value=match["location"], inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer

        # Danh sách người chơi
        player_list = "\n".join(
            [f"  {i+1}. {name}" for i, name in enumerate(match["players"].values())]
        )
        embed.add_field(
            name=f"👥 Người tham gia ({current}/{target})",
            value=player_list or "Chưa có ai",
            inline=False,
        )
        embed.add_field(name="Tiến trình", value=f"{bar} {current}/{target}", inline=False)

        embed.set_footer(text=f"ID trận: {match_id} • Gõ !join {match_id} để tham gia")
        return embed

    def create_list_embed(self) -> discord.Embed:
        """Tạo Embed hiển thị tất cả các trận đang mở."""
        matches = self.get_active_matches()
        if not matches:
            embed = discord.Embed(
                title="📋 Danh sách trận đang mở",
                description="Hiện tại chưa có trận nào đang mở.\nGõ `!mo-tran` hoặc nhắn rủ thể thao để mở trận mới!",
                color=discord.Color.greyple(),
            )
            return embed

        embed = discord.Embed(
            title="📋 Danh sách trận đang mở",
            color=discord.Color.gold(),
        )
        for m in matches:
            current = len(m["players"])
            target = m["target_players"]
            # Lấy emoji từ config
            sport_lower = m["sport"].lower()
            style = DEFAULT_SPORT_STYLE
            for sport_key, sport_style in SPORT_EMOJI_MAP.items():
                if sport_key in sport_lower:
                    style = sport_style
                    break
            sport_emoji = style["emoji"]

            embed.add_field(
                name=f"{sport_emoji} {m['sport']} — {m['time']}",
                value=f"📍 {m['location']} | 👥 {current}/{target}\n`!join {m['id']}`",
                inline=False,
            )
        embed.set_footer(text="Gõ !join <ID trận> để tham gia")
        return embed

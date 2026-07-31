"""
campus_map.py — Toạ độ lưới (grid) của các toà nhà VinUni + hàm vẽ ẢNH THẬT
chỉ đường, để gửi cho user trên Discord.

Vì sao cần file này: trước đây khi user nhờ "vẽ biểu đồ/sơ đồ đường đi",
agent chỉ in ra cú pháp Mermaid dạng chữ — nhưng Discord KHÔNG render được
Mermaid, chỉ hiện nguyên văn code, trông như bot bị lỗi. File này vẽ ra 1
file PNG thật bằng Pillow, gửi kèm như ảnh đính kèm — xem draw_route_diagram
trong tools.py và cách bot.py đính kèm ảnh vào tin nhắn Discord.

Toạ độ ở đây là toạ độ TƯƠNG ĐỐI theo lưới (không phải GPS thật) — dựng lại
đúng theo mô tả trong data/knowledge_base.txt, mục "VỊ TRÍ TƯƠNG ĐỐI" và
"SƠ ĐỒ ĐỒ THỊ DI CHUYỂN GIỮA CÁC TÒA". Nếu sau này cẩm nang đổi vị trí toà
nào, sửa lại đúng ở POSITIONS/EDGES cho khớp.
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data" / "tmp_diagrams"
FONT_DIR = BASE_DIR / "data" / "fonts"

# Ảnh vẽ ra bị NGƯỜI DÙNG THẬT báo là "rất mờ" — nguyên nhân thật KHÔNG
# phải do độ phân giải mà do _load_font() trước đây chỉ trỏ tới đường dẫn
# font hệ điều hành macOS (/System/Library/Fonts/...). Trên máy khác (Linux
# server chạy bot thật, máy đồng đội không phải Mac...) đường dẫn đó không
# tồn tại, Pillow âm thầm rơi về ImageFont.load_default() — 1 font bitmap
# CỐ ĐỊNH ~10px, không scale được, nhìn như bị mờ/vỡ nét khi đặt trong ảnh
# lớn. Fix: đóng gói THẲNG font Noto Sans (đọc được đầy đủ dấu tiếng Việt,
# giấy phép SIL Open Font License — được phép đi kèm trong repo) ngay trong
# data/fonts/, dùng đường dẫn tương đối nên chạy đúng trên MỌI máy.
SCALE = 2  # render ở độ phân giải gấp đôi rồi để Discord tự co lại -> nét hơn khi phóng to

# ---- Toạ độ lưới: x = Tây(0) -> Đông tăng dần; y = Nam(0) -> Bắc tăng dần ----
POSITIONS = {
    "CongDaiLo": (1, 0),
    "QuangTruong": (1, 1),
    "ToaC": (0, 2), "ToaI": (1, 2), "ToaE": (2, 2), "ToaF": (2.8, 1.6),
    "Parking": (0, 3), "ToaA": (1, 3), "Startup": (2, 3),
    "ToaH": (0, 4), "ToaG": (1, 4), "ToaB": (2, 4),
    "ToaL": (1, 5), "ToaK": (2, 5), "ToaJ": (3, 5),
    "SanHo": (2, 6),
}

LABELS = {
    "CongDaiLo": "Cổng Đại Lộ\n(Cổng chính)",
    "QuangTruong": "Quảng trường\ntrung tâm",
    "ToaC": "Tòa C\n(Giảng dạy)",
    "ToaI": "Tòa I\n(Tháp Hiệu bộ)",
    "ToaE": "Tòa E\n(Căn tin)",
    "ToaF": "Tòa F\n(Mô phỏng)",
    "Parking": "Bãi giữ xe",
    "ToaA": "Tòa A\n(Thư viện)",
    "Startup": "Triển lãm\nkhởi nghiệp",
    "ToaH": "Tòa H\n(In 3D/CNC)",
    "ToaG": "Tòa G\n(Superlab)",
    "ToaB": "Tòa B\n(Hội trường)",
    "ToaL": "Tòa L\n(Sân bóng)",
    "ToaK": "Tòa K\n(Gym/Bể bơi)",
    "ToaJ": "Tòa J\n(Ký túc xá)",
    "SanHo": "Cổng San Hồ",
}

# Đồ thị 2 chiều (đi bộ được cả 2 hướng) — mô phỏng đúng các cạnh trong sơ đồ
# mermaid ở knowledge_base.txt (kể cả cạnh 1 chiều "-->" cũng cho đi bộ
# ngược lại được, vì đó là hướng đi bộ gợi ý chứ không phải đường 1 chiều
# giao thông thật).
EDGES = [
    ("CongDaiLo", "QuangTruong"), ("QuangTruong", "ToaI"), ("ToaI", "ToaA"), ("ToaA", "ToaG"),
    ("ToaC", "ToaI"), ("ToaI", "ToaE"), ("Parking", "ToaA"), ("ToaA", "Startup"),
    ("ToaH", "ToaG"), ("ToaG", "ToaB"), ("ToaE", "ToaF"),
    ("ToaG", "ToaL"), ("ToaB", "ToaK"), ("ToaK", "ToaJ"),
    ("SanHo", "ToaL"), ("SanHo", "ToaK"), ("SanHo", "ToaJ"),
]

# Từ đồng nghĩa / cách gọi tự nhiên -> đúng mã toà trong POSITIONS.
ALIASES = {
    "a": "ToaA", "tòa a": "ToaA", "thư viện": "ToaA", "library": "ToaA", "elab": "ToaA",
    "b": "ToaB", "tòa b": "ToaB", "hội trường": "ToaB",
    "c": "ToaC", "tòa c": "ToaC", "giảng dạy": "ToaC", "lớp học": "ToaC",
    "e": "ToaE", "tòa e": "ToaE", "căn tin": "ToaE", "canteen": "ToaE",
    "f": "ToaF", "tòa f": "ToaF", "mô phỏng": "ToaF",
    "g": "ToaG", "tòa g": "ToaG", "superlab": "ToaG", "it support": "ToaG",
    "h": "ToaH", "tòa h": "ToaH", "in 3d": "ToaH", "cnc": "ToaH",
    "i": "ToaI", "tòa i": "ToaI", "tháp hiệu bộ": "ToaI", "hiệu bộ": "ToaI",
    "j": "ToaJ", "tòa j": "ToaJ", "ký túc xá": "ToaJ", "ktx": "ToaJ",
    "k": "ToaK", "tòa k": "ToaK", "gym": "ToaK", "bể bơi": "ToaK", "phòng gym": "ToaK", "hồ bơi": "ToaK",
    "l": "ToaL", "tòa l": "ToaL", "sân bóng": "ToaL", "sân vận động": "ToaL", "sân bóng đá": "ToaL",
    "bãi giữ xe": "Parking", "bãi xe": "Parking", "parking": "Parking",
    "cổng san hồ": "SanHo", "san hồ": "SanHo",
    "quảng trường": "QuangTruong",
    "cổng chính": "CongDaiLo", "cổng đại lộ": "CongDaiLo",
    "khởi nghiệp": "Startup", "triển lãm khởi nghiệp": "Startup",
}


def resolve_building(name: str):
    """
    Quy 1 tên toà/địa điểm user gõ tự nhiên về đúng mã trong POSITIONS.
    None nếu không nhận ra.

    LƯU Ý: các alias 1 ký tự ("a", "b", "g"...) chỉ được khớp CHÍNH XÁC
    (key == alias) — không được dùng để khớp gần đúng theo kiểu substring,
    vì gần như MỌI câu tiếng Việt đều tình cờ chứa 1 chữ cái đơn lẻ nào đó
    (vd "không" chứa "g", "không có" chứa "g"...), dễ đoán nhầm toà hoàn
    toàn không liên quan.
    """
    if not name:
        return None
    key = name.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    best, best_len = None, 0
    for alias, code in ALIASES.items():
        if len(alias) < 2:
            continue  # bỏ qua alias 1 ký tự khi khớp gần đúng
        if alias in key and len(alias) > best_len:
            best, best_len = code, len(alias)
    return best


def _shortest_path(start: str, end: str):
    """BFS tìm đường đi ngắn nhất (theo số bước) trên đồ thị EDGES (2 chiều)."""
    adj = {}
    for a, b in EDGES:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if start not in adj or end not in adj:
        return None
    if start == end:
        return [start]
    visited = {start}
    queue = deque([[start]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        for nxt in adj.get(node, []):
            if nxt == end:
                return path + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                queue.append(path + [nxt])
    return None


def _load_font(size: int, bold: bool = False):
    """
    Thử lần lượt: (1) font Noto Sans đóng gói SẴN trong repo (đọc đủ dấu
    tiếng Việt, chạy được trên MỌI máy vì không phụ thuộc OS) — ưu tiên
    cao nhất; (2) font Arial của macOS (chỉ có nếu chạy trên Mac); (3) font
    bitmap mặc định của Pillow (LUÔN có, nhưng cỡ cố định ~10px, nhìn mờ/vỡ
    nét — chỉ dùng khi cả 2 lựa chọn trên đều thất bại).
    """
    bundled_name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
    try:
        return ImageFont.truetype(str(FONT_DIR / bundled_name), size)
    except OSError:
        pass
    mac_name = "Arial Bold.ttf" if bold else "Arial Unicode.ttf"
    try:
        return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{mac_name}", size)
    except OSError:
        return ImageFont.load_default()


def render_route_image(from_code: str, to_code: str) -> Path:
    """
    Vẽ ảnh PNG sơ đồ campus: làm mờ các toà không liên quan, tô đậm điểm
    bắt đầu (xanh lá) / điểm đến (đỏ) + đường đi ngắn nhất giữa 2 toà (xanh
    dương). Trả về đường dẫn file PNG đã lưu trong data/tmp_diagrams/.
    """
    path_nodes = _shortest_path(from_code, to_code) or [from_code, to_code]
    path_set = set(path_nodes)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    margin, cell = 90 * SCALE, 130 * SCALE
    xs = [p[0] for p in POSITIONS.values()]
    ys = [p[1] for p in POSITIONS.values()]
    width = int(margin * 2 + max(xs) * cell + 40 * SCALE)
    height = int(margin * 2 + max(ys) * cell + 60 * SCALE)

    def to_px(code):
        x, y = POSITIONS[code]
        return margin + x * cell, height - margin - y * cell  # lật trục y: Bắc ở trên ảnh

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = _load_font(15 * SCALE)
    font_bold = _load_font(16 * SCALE, bold=True)
    font_title = _load_font(22 * SCALE, bold=True)

    from_label = LABELS.get(from_code, from_code).splitlines()[0]
    to_label = LABELS.get(to_code, to_code).splitlines()[0]
    # Dùng "->" (ASCII thuần) thay vì ký tự "→" — Noto Sans (font đóng gói
    # trong repo) không có glyph mũi tên này, sẽ hiện ô vuông tofu bị lỗi.
    draw.text((margin, 20 * SCALE), f"Sơ đồ đường đi: {from_label} -> {to_label}", fill="black", font=font_title)

    for a, b in EDGES:
        draw.line([to_px(a), to_px(b)], fill="#cccccc", width=3 * SCALE)
    for a, b in zip(path_nodes, path_nodes[1:]):
        draw.line([to_px(a), to_px(b)], fill="#1a73e8", width=7 * SCALE)

    box_w, box_h = 96 * SCALE, 48 * SCALE
    for code in POSITIONS:
        px, py = to_px(code)
        is_start, is_end = code == from_code, code == to_code
        on_path = code in path_set
        if is_start:
            fill, outline, text_color = "#34a853", "#1e7e34", "white"
        elif is_end:
            fill, outline, text_color = "#ea4335", "#b31412", "white"
        elif on_path:
            fill, outline, text_color = "#d2e3fc", "#1a73e8", "black"
        else:
            fill, outline, text_color = "#f1f3f4", "#9aa0a6", "black"

        rect = [px - box_w / 2, py - box_h / 2, px + box_w / 2, py + box_h / 2]
        draw.rounded_rectangle(rect, radius=8 * SCALE, fill=fill, outline=outline, width=2 * SCALE)

        label = LABELS.get(code, code)
        f = font_bold if (is_start or is_end or on_path) else font
        bbox = draw.multiline_textbbox((0, 0), label, font=f, align="center")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.multiline_text((px - tw / 2, py - th / 2), label, fill=text_color, font=f, align="center")

    # Vẽ mũi tên chỉ Bắc bằng hình học (không phụ thuộc glyph Unicode của font)
    compass_x, compass_y = width - 70 * SCALE, height - margin + 35 * SCALE
    draw.polygon(
        [
            (compass_x, compass_y - 14 * SCALE),
            (compass_x - 7 * SCALE, compass_y + 6 * SCALE),
            (compass_x + 7 * SCALE, compass_y + 6 * SCALE),
        ],
        fill="black",
    )
    label = "Bắc"
    bbox = draw.textbbox((0, 0), label, font=font_bold)
    draw.text((compass_x - (bbox[2] - bbox[0]) / 2, compass_y + 10 * SCALE), label, fill="black", font=font_bold)

    out_path = OUT_DIR / f"route_{from_code}_{to_code}.png"
    img.save(out_path)
    return out_path

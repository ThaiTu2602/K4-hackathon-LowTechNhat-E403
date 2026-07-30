import json

class MatchManager:
    def __init__(self):
        # Lưu trữ các trận đấu đang mở. Key là ID tin nhắn/trận đấu, Value là thông tin trận.
        # Ví dụ: {'123456': {'sport': 'bong-da', 'time': '17h', 'location': 'san-bong', 'players': ['UserA', 'UserB']}}
        self.active_matches = {}

    def create_match(self, match_id, sport, time, location, creator):
        """Tạo một trận đấu mới và lưu vào bộ nhớ."""
        self.active_matches[match_id] = {
            'sport': sport,
            'time': time,
            'location': location,
            'players': [creator],
            'creator': creator
        }
        return self.active_matches[match_id]

    def join_match(self, match_id, user):
        """Thêm user vào trận đấu. Trả về True nếu thành công, False nếu không tìm thấy trận."""
        if match_id in self.active_matches:
            if user not in self.active_matches[match_id]['players']:
                self.active_matches[match_id]['players'].append(user)
            return True
        return False

    def is_match_full(self, match_id, target_players=10):
        """Kiểm tra xem trận đã đủ người chưa."""
        if match_id in self.active_matches:
            return len(self.active_matches[match_id]['players']) >= target_players
        return False

# TODO (Thành viên 2): Viết thêm các hàm xử lý xóa trận, lấy danh sách người chơi, rời trận.

import random
import threading
import time
import uuid

TEST_TARGET_COLORS = {
    "빨강": (216, 58, 58),    # #D83A3A
    "초록": (58, 155, 85),   # #3A9B55
    "갈색": (139, 90, 60),   # #8B5A3C
}

TOTAL_ROUNDS = 3

AVATARS = ["🐶", "🐱", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷"]

class GameRoom:
    """한 개 방의 참가자와 게임 상태를 메모리에서 관리합니다."""
    def __init__(self):
        self._lock = threading.Lock()
        self.status = "waiting"  # waiting | playing | round_result
        self.players = {}
        self.target = None
        self.target_name = None
        self.started_at = None
        self.duration = 60
        self.round = 0
        self.total_rounds = TOTAL_ROUNDS
        self.results_revealed = False
        self._color_queue = []

    def reset(self):
        with self._lock:
            self.status = "waiting"
            self.players = {}
            self.target = None
            self.target_name = None
            self.started_at = None
            self.round = 0
            self.results_revealed = False
            self._color_queue = []

    def add_player(self, nickname, avatar=None):
        nickname = nickname.strip()
        if not 1 <= len(nickname) <= 16:
            raise ValueError("닉네임은 1~16자로 입력해주세요.")
        if avatar not in AVATARS:
            avatar = random.choice(AVATARS)
        with self._lock:
            if self.status != "waiting":
                raise ValueError("게임이 이미 시작되었습니다.")
            if any(p["nickname"].casefold() == nickname.casefold() for p in self.players.values()):
                raise ValueError("이미 사용 중인 닉네임입니다.")
            player_id = uuid.uuid4().hex
            self.players[player_id] = {
                "nickname": nickname,
                "avatar": avatar,
                "submission_status": "waiting",
                "score": None,
                "total_score": 0.0,
            }
            return player_id

    def _next_color(self):
        if not self._color_queue:
            pool = list(TEST_TARGET_COLORS.items())
            random.shuffle(pool)
            self._color_queue = pool
        return self._color_queue.pop(0)

    def _begin_round(self):
        # 호출 전 _lock을 이미 잡고 있어야 한다.
        self.target_name, self.target = self._next_color()
        self.started_at = time.time()
        self.status = "playing"
        self.results_revealed = False
        for player in self.players.values():
            player["submission_status"] = "waiting"
            player["score"] = None

    def start(self):
        with self._lock:
            if self.status != "waiting":
                raise ValueError("진행 중이거나 종료된 게임입니다. 먼저 방을 초기화해주세요.")
            if not self.players:
                raise ValueError("참가자가 한 명 이상 필요합니다.")
            self.round = 1
            self._begin_round()

    def next_round(self):
        with self._lock:
            if self.status != "round_result":
                raise ValueError("라운드 결과 화면에서만 다음 라운드를 시작할 수 있습니다.")
            if self.round >= self.total_rounds:
                raise ValueError("모든 라운드가 종료되었습니다.")
            self.round += 1
            self._begin_round()

    def reveal_results(self):
        with self._lock:
            if self.status != "round_result" or self.round < self.total_rounds:
                raise ValueError("최종 라운드 결과 화면에서만 결과를 발표할 수 있습니다.")
            self.results_revealed = True

    def begin_submission(self, player_id):
        with self._lock:
            if player_id not in self.players:
                raise LookupError("참가자 정보가 없습니다.")
            if self.status != "playing" or time.time() >= self.started_at + self.duration:
                raise ValueError("제출 시간이 종료되었습니다.")
            if self.players[player_id]["submission_status"] != "waiting":
                raise ValueError("사진은 한 번만 제출할 수 있습니다.")
            self.players[player_id]["submission_status"] = "processing"

    def complete_submission(self, player_id, score):
        with self._lock:
            if player_id not in self.players:
                raise LookupError("참가자 정보가 없습니다.")
            if self.players[player_id]["submission_status"] != "processing":
                raise ValueError("처리 중인 제출이 아닙니다.")
            self.players[player_id]["submission_status"] = "completed"
            self.players[player_id]["score"] = score
            total = self.players[player_id]["total_score"] + score["final_score"]
            self.players[player_id]["total_score"] = round(total, 1)

    def fail_submission(self, player_id):
        with self._lock:
            if player_id in self.players and self.players[player_id]["submission_status"] == "processing":
                self.players[player_id]["submission_status"] = "waiting"

    def _update_status(self):
        if self.status == "playing" and time.time() >= self.started_at + self.duration:
            self.status = "round_result"

    def has_player(self, player_id):
        with self._lock:
            return player_id in self.players

    def target_rgb(self):
        with self._lock:
            return self.target

    def snapshot(self, player_id=None):
        with self._lock:
            self._update_status()
            players = [
                {
                    "nickname": player["nickname"],
                    "avatar": player["avatar"],
                    "submission_status": player["submission_status"],
                    "submitted": player["submission_status"] == "completed",
                    "score": player["score"],
                    "total_score": player["total_score"],
                    "me": pid == player_id,
                }
                for pid, player in self.players.items()
            ]
            leaderboard = sorted(
                (
                    {
                        "nickname": player["nickname"],
                        "avatar": player["avatar"],
                        "total_score": player["total_score"],
                        "me": pid == player_id,
                    }
                    for pid, player in self.players.items()
                ),
                key=lambda entry: -entry["total_score"],
            )
            remaining = 0
            if self.status == "playing":
                remaining = max(0, int(self.started_at + self.duration - time.time() + 0.999))
            return {
                "status": self.status,
                "round": self.round,
                "total_rounds": self.total_rounds,
                "is_final_round": self.round >= self.total_rounds,
                "results_revealed": self.results_revealed,
                "players": players,
                "leaderboard": leaderboard,
                "submitted_count": sum(
                    player["submission_status"] == "completed" for player in self.players.values()
                ),
                "processing_count": sum(
                    player["submission_status"] == "processing" for player in self.players.values()
                ),
                "target": color_hex(self.target) if self.target else None,
                "target_name": self.target_name,
                "remaining": remaining,
                "duration": self.duration,
            }

    def dev_force_status(self, status, final=False, revealed=False):
        """개발용: 실제 흐름 없이 원하는 화면 상태로 강제 이동한다. 실서비스 로직에서는 쓰지 않는다."""
        with self._lock:
            self.status = status
            if status == "playing":
                self.round = self.round or 1
                self.target_name, self.target = self._next_color()
                self.started_at = time.time()
            elif status == "round_result":
                self.round = self.total_rounds if final else 1
                self.results_revealed = revealed

def color_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

room = GameRoom()

"""개발용 라우트: 실제 게임 흐름을 거치지 않고 각 화면을 바로 볼 수 있게 한다.
COLORHUNT_DEV=1 환경변수일 때만 app.py에서 등록된다. 행사 당일에는 절대 켜두지 않는다.
"""
import random

from flask import Blueprint, redirect, render_template, session, url_for
from backend.game_state import room

dev_bp = Blueprint("dev", __name__, url_prefix="/dev")

PLAYER_COUNT = 20


@dev_bp.get("/")
def dev_index():
    return render_template("dev.html")


def _populate(count=PLAYER_COUNT, with_scores=False, submission_mix=False):
    """방을 초기화하고 나(me) + 가짜 참가자 (count-1)명을 채운다."""
    room.reset()
    session.pop("player_id", None)
    my_id = room.add_player("나")
    session["player_id"] = my_id
    for i in range(1, count):
        room.add_player(f"참가자{i:02d}")

    if with_scores:
        for player in room.players.values():
            player["total_score"] = round(random.uniform(20, 98), 1)

    if submission_mix:
        statuses = ["waiting", "processing", "completed"]
        for player in room.players.values():
            status = random.choice(statuses)
            player["submission_status"] = status
            if status == "completed":
                player["score"] = {"final_score": round(random.uniform(20, 98), 1)}

    return my_id


@dev_bp.get("/join")
def as_join():
    room.reset()
    session.pop("player_id", None)
    return redirect(url_for("player.join_page"))


@dev_bp.get("/waiting")
def as_waiting():
    _populate()
    return redirect(url_for("player.waiting_page"))


@dev_bp.get("/play")
def as_play():
    _populate()
    room.dev_force_status("playing")
    return redirect(url_for("player.play_page"))


@dev_bp.get("/leaderboard")
def as_leaderboard():
    _populate(with_scores=True)
    room.dev_force_status("round_result", final=False)
    return redirect(url_for("player.leaderboard_page"))


@dev_bp.get("/leaderboard-final-waiting")
def as_leaderboard_final_waiting():
    _populate(with_scores=True)
    room.dev_force_status("round_result", final=True, revealed=False)
    return redirect(url_for("player.leaderboard_page"))


@dev_bp.get("/leaderboard-final-revealed")
def as_leaderboard_final_revealed():
    _populate(with_scores=True)
    room.dev_force_status("round_result", final=True, revealed=True)
    return redirect(url_for("player.leaderboard_page"))


@dev_bp.get("/admin-login")
def as_admin_login():
    session.pop("is_admin", None)
    return redirect(url_for("admin.admin_page"))


@dev_bp.get("/admin-waiting")
def as_admin_waiting():
    _populate()
    session["is_admin"] = True
    return redirect(url_for("admin.admin_page"))


@dev_bp.get("/admin-playing")
def as_admin_playing():
    _populate(submission_mix=True)
    room.dev_force_status("playing")
    session["is_admin"] = True
    return redirect(url_for("admin.admin_page"))


@dev_bp.get("/admin-result")
def as_admin_result():
    _populate(with_scores=True)
    room.dev_force_status("round_result", final=False)
    session["is_admin"] = True
    return redirect(url_for("admin.admin_page"))


@dev_bp.get("/admin-result-final")
def as_admin_result_final():
    _populate(with_scores=True)
    room.dev_force_status("round_result", final=True, revealed=False)
    session["is_admin"] = True
    return redirect(url_for("admin.admin_page"))

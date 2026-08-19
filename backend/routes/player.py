from flask import Blueprint, redirect, render_template, session, url_for
from backend.game_state import AVATARS, room
from backend.i18n import translate

player_bp = Blueprint("player", __name__)

_ENDPOINT_BY_STATUS = {
    "playing": "player.play_page",
    "round_result": "player.leaderboard_page",
}

@player_bp.get("/")
def intro_page():
    player_id = session.get("player_id")
    if room.has_player(player_id):
        state = room.snapshot(player_id)
        endpoint = _ENDPOINT_BY_STATUS.get(state["status"], "player.waiting_page")
        return redirect(url_for(endpoint))
    return render_template("intro.html")

@player_bp.get("/join")
def join_page():
    player_id = session.get("player_id")
    state = room.snapshot(player_id)
    if room.has_player(player_id):
        endpoint = _ENDPOINT_BY_STATUS.get(state["status"], "player.waiting_page")
        return redirect(url_for(endpoint))
    if state["status"] != "waiting":
        return render_template("message.html", message=translate("game_already_started")), 403
    return render_template("join.html", avatars=AVATARS)

@player_bp.get("/waiting")
def waiting_page():
    player_id = session.get("player_id")
    if not room.has_player(player_id):
        return redirect(url_for("player.join_page"))
    state = room.snapshot(player_id)
    if state["status"] in _ENDPOINT_BY_STATUS:
        return redirect(url_for(_ENDPOINT_BY_STATUS[state["status"]]))
    return render_template("waiting.html")

@player_bp.get("/play")
def play_page():
    player_id = session.get("player_id")
    state = room.snapshot(player_id)
    if not room.has_player(player_id):
        return redirect(url_for("player.join_page"))
    if state["status"] == "round_result":
        return redirect(url_for("player.leaderboard_page"))
    if state["status"] != "playing":
        return redirect(url_for("player.waiting_page"))
    return render_template(
        "play.html",
        target=state["target"],
        duration=state["remaining"],
        round=state["round"],
        total_rounds=state["total_rounds"],
    )

@player_bp.get("/leaderboard")
def leaderboard_page():
    player_id = session.get("player_id")
    if not room.has_player(player_id):
        return redirect(url_for("player.join_page"))
    state = room.snapshot(player_id)
    if state["status"] == "playing":
        return redirect(url_for("player.play_page"))
    if state["status"] != "round_result":
        return redirect(url_for("player.waiting_page"))
    return render_template(
        "leaderboard.html",
        round=state["round"],
        total_rounds=state["total_rounds"],
        is_final=state["is_final_round"],
    )

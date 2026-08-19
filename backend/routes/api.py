from flask import Blueprint, jsonify, request, session
from backend.game_state import room
from backend.image_analysis import analyze_photo
from backend.i18n import translate, translate_color, translate_error

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.post("/join")
def join():
    payload = request.get_json(silent=True) or {}
    nickname = payload.get("nickname", "")
    avatar = payload.get("avatar", "")
    try:
        session["player_id"] = room.add_player(nickname, avatar)
    except ValueError as exc:
        return jsonify(error=translate_error(exc)), 409
    return jsonify(ok=True)

@api_bp.get("/state")
def state():
    player_id = session.get("player_id")
    admin_request = request.args.get("admin") == "1"
    if admin_request and not session.get("is_admin"):
        return jsonify(error=translate("admin_required")), 403
    if not admin_request and not room.has_player(player_id):
        return jsonify(error=translate("player_missing")), 401
    snapshot = room.snapshot(player_id)
    if snapshot["target_name"]:
        snapshot["target_name"] = translate_color(snapshot["target_name"])
    return jsonify(snapshot)

@api_bp.post("/submit")
def submit_photo():
    player_id = session.get("player_id")
    if not room.has_player(player_id):
        return jsonify(error=translate("player_missing")), 401
    state = room.snapshot(player_id)
    if state["status"] != "playing":
        return jsonify(error=translate("time_closed")), 409
    current_player = next(player for player in state["players"] if player["me"])
    if current_player["submission_status"] != "waiting":
        return jsonify(error=translate("already_submitted")), 409
    photo = request.files.get("photo")
    if photo is None or not photo.filename:
        return jsonify(error=translate("photo_required")), 400
    submission_started = False
    try:
        room.begin_submission(player_id)
        submission_started = True
        result = analyze_photo(photo, room.target_rgb())
        time_score = round(state["remaining"] / state["duration"] * 20, 1)
        final_score = round(result["color_score"] * 0.8 + time_score, 1)
        result.update(time_score=time_score, final_score=final_score)
        stored_result = {key: value for key, value in result.items() if key != "preview"}
        room.complete_submission(player_id, stored_result)
    except ValueError as exc:
        if submission_started:
            room.fail_submission(player_id)
        return jsonify(error=translate_error(exc)), 409
    except RuntimeError as exc:
        if submission_started:
            room.fail_submission(player_id)
        return jsonify(error=translate("analysis_failed")), 503
    return jsonify(result)

@api_bp.post("/start")
def start():
    if not session.get("is_admin"):
        return jsonify(error=translate("admin_required")), 403
    try:
        room.start()
    except ValueError as exc:
        return jsonify(error=translate_error(exc)), 409
    return jsonify(ok=True)

@api_bp.post("/next_round")
def next_round():
    if not session.get("is_admin"):
        return jsonify(error=translate("admin_required")), 403
    try:
        room.next_round()
    except ValueError as exc:
        return jsonify(error=translate_error(exc)), 409
    return jsonify(ok=True)

@api_bp.post("/reveal_results")
def reveal_results():
    if not session.get("is_admin"):
        return jsonify(error=translate("admin_required")), 403
    try:
        room.reveal_results()
    except ValueError as exc:
        return jsonify(error=translate_error(exc)), 409
    return jsonify(ok=True)

@api_bp.post("/reset")
def reset():
    if not session.get("is_admin"):
        return jsonify(error=translate("admin_required")), 403
    room.reset()
    return jsonify(ok=True)

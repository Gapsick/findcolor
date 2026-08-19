import os

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from backend.qr_utils import make_qr_data_url
from backend.i18n import translate

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET", "POST"])
@admin_bp.route("/host", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        if request.form.get("pin") != current_app.config["ADMIN_PIN"]:
            return render_template("admin_login.html", error=translate("pin_invalid")), 403
        session["is_admin"] = True
        return redirect(url_for("admin.admin_page"))
    if not session.get("is_admin"):
        return render_template("admin_login.html", error=None)
    public_url = os.environ.get("COLORHUNT_PUBLIC_URL")
    base = public_url.rstrip("/") if public_url else request.url_root.rstrip("/")
    join_url = base + "/"
    if session.get("language") == "ja":
        join_url += "?lang=ja"
    return render_template("admin.html", join_url=join_url, qr=make_qr_data_url(join_url))

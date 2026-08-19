import os
import threading
from pathlib import Path

from flask import Flask
from backend.routes.admin import admin_bp
from backend.routes.api import api_bp
from backend.routes.player import player_bp
from backend.i18n import JS_TRANSLATIONS, current_language, translate


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_ROOT / "templates"),
        static_folder=str(FRONTEND_ROOT / "static"),
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("COLORHUNT_SECRET", os.urandom(32)),
        ADMIN_PIN=os.environ.get("COLORHUNT_ADMIN_PIN", "1234"),
    )
    if test_config:
        app.config.update(test_config)
    app.register_blueprint(player_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_i18n():
        language = current_language()
        return {
            "lang": language,
            "other_lang": "ja" if language == "ko" else "ko",
            "t": translate,
            "i18n_js": JS_TRANSLATIONS[language],
        }
    if test_config is None and os.environ.get("COLORHUNT_WARMUP", "1") == "1":
        from backend.yolo_segmentation import warmup

        threading.Thread(target=warmup, daemon=True, name="yolo-warmup").start()
    return app

app = create_app()

if __name__ == "__main__":
    print("참가자: http://<PC의-IP>:5000")
    print("방장: http://<PC의-IP>:5000/host")
    app.run(host="0.0.0.0", port=5000, debug=False)

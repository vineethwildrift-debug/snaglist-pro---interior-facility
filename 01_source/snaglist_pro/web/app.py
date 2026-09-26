"""
Snaglist Pro — Web UI (Flask)

Launch:
    python -m snaglist_pro --web
    flask --app snaglist_pro.web.app run --port 5000
"""

import os
import sys
import time
import uuid
import json
import threading
import zipfile
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template, send_file, url_for, session, redirect

os.environ.setdefault("TQDM_DISABLE", "1")

def get_app_data_dir() -> Path:
    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base_dir) / "SnaglistPro"
    return Path.home() / ".snaglistpro"


def _resolve_asset_dir(name: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "snaglist_pro" / "web" / name
        if candidate.exists():
            return str(candidate)
    return str(Path(__file__).resolve().parent / name)


app = Flask(
    __name__,
    template_folder=_resolve_asset_dir("templates"),
    static_folder=_resolve_asset_dir("static"),
)
app.config["SECRET_KEY"] = os.environ.get("SNAGLIST_SECRET", "snaglist-pro-dev")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

APP_DATA_DIR = get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(APP_DATA_DIR / "web_uploads")
app.config["OUTPUT_FOLDER"] = str(APP_DATA_DIR / "web_output")

UPLOAD_DIR = Path(app.config["UPLOAD_FOLDER"])
OUTPUT_DIR = Path(app.config["OUTPUT_FOLDER"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

jobs = {}


def _is_logged_in():
    return session.get("user") is not None


def _require_login():
    if not _is_logged_in():
        return redirect("/")
    return None


@app.before_request
def _enforce_session_timeout():
    if session.get("user"):
        last = session.get("last_activity")
        if last and time.time() - last > 1800:
            session.clear()
            return redirect("/")
        session["last_activity"] = time.time()


def _cleanup_old_jobs():
    import time
    cutoff = time.time() - (7 * 24 * 3600)
    for job_dir in UPLOAD_DIR.iterdir():
        if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)
    for job_dir in OUTPUT_DIR.iterdir():
        if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)


_cleanup_old_jobs()


def _run_pipeline(job_id: str, zip_path: str, checklist_path: str | None, output_dir: str, ai_enabled: bool = True, fast_mode: bool = False, project_name: str = ""):
    try:
        from snaglist_pro.pipeline import SnaglistPipeline
        from snaglist_pro.config import settings
        pipeline = SnaglistPipeline()
        
        original_ai_enabled = settings.ai_enabled
        original_max_calls = settings.max_ai_calls_per_run
        original_client = settings.project_default_client
        
        if not ai_enabled:
            settings.ai_enabled = False
            settings.max_ai_calls_per_run = 0
        
        if project_name:
            settings.project_default_client = project_name
        
        def progress_callback(step, message, percent):
            with lock:
                if cancelled.get(job_id):
                    raise KeyboardInterrupt("Job cancelled by user")
                progress[job_id] = {"step": step, "message": message, "percent": percent}
        
        try:
            result = pipeline.run(
                zip_path=zip_path,
                checklist_path=checklist_path or "",
                output_dir=output_dir,
                progress_callback=progress_callback,
                fast_mode=fast_mode,
                project_name=project_name or None,
            )
            with lock:
                jobs[job_id] = {
                    "status": "done",
                    "result": result,
                    "finished_at": datetime.now().isoformat(),
                }
                progress[job_id] = {"step": "complete", "message": "Done", "percent": 100}
        finally:
            settings.ai_enabled = original_ai_enabled
            settings.max_ai_calls_per_run = original_max_calls
            settings.project_default_client = original_client
            
    except Exception as exc:
        with lock:
            jobs[job_id] = {
                "status": "error",
                "error": str(exc),
                "finished_at": datetime.now().isoformat(),
            }
            progress[job_id] = {"step": "error", "message": str(exc), "percent": 0}


@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "")
        app_user = os.environ.get("SNAGLIST_APP_USERNAME")
        app_password = os.environ.get("SNAGLIST_APP_PASSWORD")
        if app_user and app_password and username == app_user and password == app_password:
            session.permanent = True
            session["user"] = username
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid username or password."), 401

    if _is_logged_in():
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


@app.route("/dashboard")
def index():
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    if "zip" not in request.files:
        return jsonify({"error": "No ZIP file provided"}), 400

    file = request.files["zip"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    checklist_file = request.files.get("checklist")
    ai_enabled = request.form.get("ai_enabled", "1") == "1"
    fast_mode = request.form.get("fast_mode", "0") == "1"
    job_id = uuid.uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    zip_path = job_dir / "input.zip"
    file.save(str(zip_path))

    checklist_path = None
    if checklist_file and checklist_file.filename:
        checklist_path = job_dir / "checklist.xlsx"
        checklist_file.save(str(checklist_path))

    output_dir = OUTPUT_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    project_name = request.form.get("project", "").strip()

    with lock:
        jobs[job_id] = {"status": "processing", "created_at": datetime.now().isoformat()}

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, str(zip_path), str(checklist_path) if checklist_path else None, str(output_dir), ai_enabled, fast_mode, project_name),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    with lock:
        cancelled[job_id] = True
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"status": "cancelled"})


@app.route("/api/history")
def job_history():
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    with lock:
        job_list = []
        for job_id, job in jobs.items():
            job_list.append({
                "job_id": job_id,
                "status": job.get("status"),
                "created_at": job.get("created_at"),
                "finished_at": job.get("finished_at"),
                "error": job.get("error"),
            })
    job_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(job_list[:50])


@app.route("/history")
def history_page():
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    return render_template("history.html")


@app.route("/api/status/<job_id>")
def status(job_id):
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    with lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/progress/<job_id>")
def progress_endpoint(job_id):
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    with lock:
        prog = progress.get(job_id)
    if not prog:
        return jsonify({"step": "queued", "message": "Waiting to start", "percent": 0})
    return jsonify(prog)


@app.route("/api/download/<job_id>")
def download(job_id):
    redirect_to_login = _require_login()
    if redirect_to_login is not None:
        return redirect_to_login
    output_dir = OUTPUT_DIR / job_id
    if not output_dir.exists():
        return jsonify({"error": "Output not found"}), 404

    regular_files = sorted(output_dir.glob("*.xlsx"))
    regular_files = [f for f in regular_files if not f.name.endswith("_gs.xlsx")]
    if regular_files:
        return send_file(str(regular_files[-1]), as_attachment=True)

    gs_files = sorted(output_dir.glob("*_gs.xlsx"))
    if gs_files:
        return send_file(str(gs_files[-1]), as_attachment=True)

    return jsonify({"error": "No Excel output found"}), 404


if __name__ == "__main__":
    from snaglist_pro.database import init_db
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)

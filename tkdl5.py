import os
import uuid
import subprocess
import requests
from flask import Flask, request, render_template, send_from_directory, jsonify, url_for

app = Flask(__name__)

# Folder for temporary downloads
DOWNLOAD_FOLDER = os.path.join(app.root_path, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def sanitize_url(url: str) -> str:
    """Basic cleanup to avoid malformed TikTok links"""
    if not url:
        return ""
    url = url.strip()
    if "tiktok.com" not in url:
        return ""
    return url.split("?")[0]  # remove tracking params


def download_with_tikwm(url: str):
    """Try Tikwm API"""
    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        resp = requests.get(api_url, timeout=10).json()
        if resp.get("data"):
            return {
                "video_url": resp["data"].get("play"),
                "thumbnail_url": resp["data"].get("cover")
            }
    except Exception:
        return None
    return None


def download_with_snaptik(url: str):
    """Try SnapTik API"""
    try:
        api_url = f"https://api.snaptik.app/api/v1/fetch?url={url}"
        resp = requests.get(api_url, timeout=10).json()
        if resp.get("video"):
            return {
                "video_url": resp.get("video"),
                "thumbnail_url": resp.get("cover")
            }
    except Exception:
        return None
    return None


def download_with_ytdlp(url: str):
    """Fallback to yt-dlp"""
    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        cmd = ["yt-dlp", "-o", filepath, url]
        subprocess.run(cmd, check=True)

        return {
            "video_url": url_for("serve_file", filename=filename),
            "thumbnail_url": None
        }
    except Exception:
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    url = sanitize_url(request.form.get("url"))
    if not url:
        return jsonify({"error": "Invalid or missing TikTok URL"}), 400

    # Try Tikwm
    result = download_with_tikwm(url)
    if result:
        return jsonify(result)

    # Fallback: SnapTik
    result = download_with_snaptik(url)
    if result:
        return jsonify(result)

    # Last resort: yt-dlp
    result = download_with_ytdlp(url)
    if result:
        return jsonify(result)

    return jsonify({"error": "Could not extract video"}), 500


@app.route("/download", methods=["POST"])
def download():
    url = sanitize_url(request.form.get("url"))
    if not url:
        return "Invalid URL", 400

    # Reuse same order
    result = download_with_tikwm(url)
    if result and result["video_url"]:
        return f"<meta http-equiv='refresh' content='0;url={result['video_url']}'>"

    result = download_with_snaptik(url)
    if result and result["video_url"]:
        return f"<meta http-equiv='refresh' content='0;url={result['video_url']}'>"

    result = download_with_ytdlp(url)
    if result and result["video_url"]:
        return f"<meta http-equiv='refresh' content='0;url={result['video_url']}'>"

    return "Download failed", 500


@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)

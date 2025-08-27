from flask import Flask, request, send_from_directory, redirect, url_for
import os, uuid, subprocess, threading, time, re, requests


app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(app.root_path, "static", "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

COOKIES_FILE = os.path.join(app.root_path, "cookies.txt")

# -------- Helpers -------- #

def sanitize_url(url: str) -> str:
    """
    Clean TikTok URLs to the base format:
    https://www.tiktok.com/@username/video/ID
    """
    if not url:
        return None
    match = re.search(r"(https?://www\.tiktok\.com/@[A-Za-z0-9._]+/video/\d+)", url)
    return match.group(1) if match else url.strip()


def download_with_tikwm(url, filepath):
    try:
        api = "https://www.tikwm.com/api/"
        res = requests.post(api, data={"url": url}, timeout=15)
        res.raise_for_status()
        data = res.json()
        if data.get("code") == 0:
            dl_url = data["data"]["play"]
            r = requests.get(dl_url, stream=True, timeout=30)
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"[TikWM error] {e}")
        return False


def download_with_snaptik(url, filepath):
    try:
        api = f"https://api.snaptik.app/api/v1/fetch?url={url}"
        res = requests.get(api, timeout=15)
        res.raise_for_status()
        data = res.json()
        if "video" in data and "urls" in data["video"]:
            dl_url = data["video"]["urls"][0]
            r = requests.get(dl_url, stream=True, timeout=30)
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"[SnapTik error] {e}")
        return False


def download_with_ytdlp(url, filepath):
    try:
        cmd = [
            "yt-dlp",
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "-o", filepath,
        ]
        if os.path.exists(COOKIES_FILE):
            cmd += ["--cookies", COOKIES_FILE]
        cmd.append(url)

        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"[yt-dlp error] {e}")
        return False


def cleanup_loop():
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_FOLDER):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 300:
                os.remove(path)
                print(f"[Cleanup] Removed {path}")
        time.sleep(300)


# -------- Routes -------- #

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/preview", methods=["POST"])
def preview_video():
    url = request.form.get("url")
    url = sanitize_url(url)
    if not url:
        return {"error": "Invalid TikTok URL"}, 400

    try:
        api = "https://www.tikwm.com/api/"
        res = requests.post(api, data={"url": url}, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("code") == 0:
            return {
                "title": data["data"].get("title"),
                "author": data["data"]["author"]["unique_id"],
                "cover": data["data"].get("cover"),
                "url": url
            }
        return {"error": "No preview available"}, 500
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/", methods=["POST"])
def download_video():
    url = request.form.get("url")
    url = sanitize_url(url)
    if not url:
        return "Invalid TikTok URL", 400

    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    # Try TikWM
    if download_with_tikwm(url, filepath):
        return redirect(url_for("serve_file", filename=filename))

    # Try SnapTik
    if download_with_snaptik(url, filepath):
        return redirect(url_for("serve_file", filename=filename))

    # Fallback: yt-dlp
    if download_with_ytdlp(url, filepath):
        return redirect(url_for("serve_file", filename=filename))

    return "❌ Failed to download video (all methods)", 500


@app.route("/downloads/<filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


# Start cleanup thread
threading.Thread(target=cleanup_loop, daemon=True).start()


if __name__ == "__main__":
    app.run(debug=True)

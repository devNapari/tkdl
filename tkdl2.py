from flask import Flask, request, send_from_directory, redirect, url_for, jsonify
import os, uuid, subprocess, threading, time, re, requests

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(app.root_path, "static", "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Utility: sanitize TikTok URLs ---
def sanitize_url(url: str) -> str:
    if not url:
        return ""
    # Remove tracking params
    clean = url.split("?")[0]
    # Ensure it's TikTok
    if not clean.startswith("http"):
        clean = "https://" + clean
    return clean.strip()

# --- API 1: TikWM ---
def download_tikwm(url: str, filepath: str):
    api = "https://www.tikwm.com/api/"
    resp = requests.post(api, data={"url": url})
    if resp.status_code != 200:
        raise Exception("TikWM request failed")
    data = resp.json()
    if data.get("code") != 0:
        raise Exception("TikWM error: " + data.get("msg", "unknown"))
    video_url = data["data"]["play"]
    r = requests.get(video_url, stream=True)
    if r.status_code != 200:
        raise Exception("TikWM video download failed")
    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

# --- API 2: SnapTik ---
def download_snaptik(url: str, filepath: str):
    api = "https://ssstik.io/abc?url=" + url
    # Note: SnapTik changes frequently; you may need to adjust parsing.
    resp = requests.get(api, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise Exception("SnapTik request failed")
    # This is a placeholder; SnapTik normally returns HTML with a redirect.
    # For production, parse it properly.
    raise Exception("SnapTik parsing not implemented")  # fallback to yt-dlp

# --- API 3: yt-dlp ---
def download_ytdlp(url: str, filepath: str):
    cmd = [
        "yt-dlp",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "-o",
        filepath,
        url,
    ]
    subprocess.run(cmd, check=True)

# --- Preview API ---
@app.route("/preview", methods=["POST"])
def preview():
    url = sanitize_url(request.form.get("url"))
    if not url:
        return jsonify({"error": "Missing TikTok URL"}), 400

    # Try TikWM for metadata
    try:
        resp = requests.post("https://www.tikwm.com/api/", data={"url": url})
        data = resp.json()
        if data.get("code") == 0:
            meta = data["data"]
            return jsonify({
                "title": meta.get("title", ""),
                "author": meta.get("author", {}).get("unique_id", ""),
                "cover": meta.get("cover", ""),
                "url": url
            })
    except Exception:
        pass

    return jsonify({"error": "Could not fetch preview"}), 500

# --- Download Route ---
@app.route("/", methods=["POST"])
def download_video():
    url = sanitize_url(request.form.get("url"))
    if not url:
        return "Missing TikTok URL", 400

    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    try:
        # Try TikWM
        try:
            download_tikwm(url, filepath)
            return redirect(url_for("serve_file", filename=filename))
        except Exception as e1:
            print("TikWM failed:", e1)

        # Try SnapTik
        try:
            download_snaptik(url, filepath)
            return redirect(url_for("serve_file", filename=filename))
        except Exception as e2:
            print("SnapTik failed:", e2)

        # Fallback: yt-dlp
        download_ytdlp(url, filepath)
        return redirect(url_for("serve_file", filename=filename))

    except Exception as e:
        return f"Error downloading video: {str(e)}", 500

# Serve index.html
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/downloads/<filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

# --- Cleanup Loop ---
def cleanup_loop():
    while True:
        now = time.time()
        for f in os.listdir(DOWNLOAD_FOLDER):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 300:
                os.remove(path)
        time.sleep(300)

threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)

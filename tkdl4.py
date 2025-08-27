from flask import Flask, request, send_from_directory, jsonify, send_file, render_template
import os, uuid, threading, time, tempfile, requests, yt_dlp, shutil

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(app.root_path, "static", "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

TEMP_BASE = os.path.join(tempfile.gettempdir(), "tkdl_temp")
os.makedirs(TEMP_BASE, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")
    #return send_from_directory("static", "index.html")

# Preview endpoint
@app.route("/preview", methods=["POST"])
def preview():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "Missing TikTok URL"}), 400

    try:
        # 1. Try TikWM API
        try:
            resp = requests.post("https://www.tikwm.com/api/", data={"url": url}, timeout=10)
            data = resp.json()
            if data.get("data"):
                return jsonify({
                    "status": "ok",
                    "thumbnail": data["data"]["cover"],
                    "author": data["data"]["author"],
                    "desc": data["data"]["title"],
                    "video": data["data"]["play"],
                })
        except Exception:
            pass

        # 2. Try SnapTik API
        try:
            resp = requests.get(f"https://ssstik.io/abc?url={url}", timeout=10)
            if resp.ok:
                return jsonify({
                    "status": "ok",
                    "thumbnail": "",
                    "author": "",
                    "desc": "",
                    "video": url,
                })
        except Exception:
            pass

        # 3. Fallback to yt-dlp
        try:
            ydl_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    "status": "ok",
                    "thumbnail": info.get("thumbnail", ""),
                    "author": info.get("uploader", ""),
                    "desc": info.get("title", ""),
                    "video": info.get("url", ""),
                })
        except Exception:
            pass

        return jsonify({"error": "Could not fetch preview"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Download endpoint — returns actual file
@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Create unique temp folder
        tmpdir = tempfile.mkdtemp(dir=TEMP_BASE)
        filepath = os.path.join(tmpdir, "tiktok.mp4")

        ydl_opts = {
            "outtmpl": filepath,
            "format": "mp4/best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Return file for browser save
        return send_file(
            filepath,
            as_attachment=True,
            download_name="tiktok.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:
        return jsonify({"error": f"yt-dlp failed: {str(e)}"}), 500


@app.route("/downloads/<filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


# Background cleanup for both static downloads and temp dirs
def cleanup_loop():
    while True:
        now = time.time()

        # clean static downloads
        for f in os.listdir(DOWNLOAD_FOLDER):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 300:
                os.remove(path)

        # clean temp download dirs
        for d in os.listdir(TEMP_BASE):
            path = os.path.join(TEMP_BASE, d)
            if os.path.isdir(path) and now - os.path.getmtime(path) > 300:
                shutil.rmtree(path, ignore_errors=True)

        time.sleep(300)

threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)

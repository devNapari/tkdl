from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
import tempfile
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Unified extractor
def extract_video_info(url):
    try:
        # Try TikWM
        api_url = "https://www.tikwm.com/api/"
        res = requests.post(api_url, data={"url": url}, timeout=10)
        data = res.json()
        if data.get("code") == 0:
            return {
                "success": True,
                "url": data["data"]["play"],
                "thumbnail": data["data"]["cover"],
                "title": data["data"]["title"] or "video"
            }
    except Exception:
        pass

    try:
        # Try SnapTik
        api_url = "https://api.snaptik.app/api/v1/video/details"
        res = requests.post(api_url, data={"url": url}, timeout=10)
        data = res.json()
        if data.get("status") == "ok":
            return {
                "success": True,
                "url": data["video"]["play"],
                "thumbnail": data["video"]["thumbnail"],
                "title": data["video"].get("title", "video")
            }
    except Exception:
        pass

    try:
        # Fallback: yt-dlp
        ydl_opts = {"quiet": True, "format": "mp4"}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "success": True,
                "url": info["url"],
                "thumbnail": info.get("thumbnail"),
                "title": info.get("title", "video")
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": False, "error": "No extractor worked."}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url.startswith("http"):
        return jsonify({"success": False, "error": "Invalid URL"})
    info = extract_video_info(url)
    return jsonify(info)


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url.startswith("http"):
        return jsonify({"success": False, "error": "Invalid URL"})

    info = extract_video_info(url)
    if not info.get("success"):
        return jsonify(info)

    try:
        # Save file temporarily
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(tmp_fd)

        r = requests.get(info["url"], stream=True, timeout=30)
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f"{info['title']}.mp4"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)

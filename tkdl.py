from flask import Flask, render_template, request, jsonify, send_file
import requests
import uuid
import os
import threading
import time

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(app.root_path, "static", "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def extract_video_info(url):
    """Unified video info extractor (using tikwm API)."""
    api_url = "https://www.tikwm.com/api/"
    try:
        res = requests.post(api_url, data={"url": url}, timeout=15)
        data = res.json()
        if data.get("code") == 0:
            return {
                "video_url": data["data"]["play"],
                "thumb_url": data["data"]["cover"],
            }
    except Exception as e:
        print(f"Error extracting video info: {e}")
    return None


def schedule_file_deletion(filepath, delay=180):
    """Delete a file after `delay` seconds."""
    def delete_later():
        time.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[CLEANUP] Deleted file: {filepath}")
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")

    threading.Thread(target=delete_later, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    url = request.json.get("url")
    info = extract_video_info(url)
    if info:
        return jsonify(info)
    return jsonify({"error": "Could not load preview."})


@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    info = extract_video_info(url)
    if not info:
        return jsonify({"error": "Download failed."}), 400

    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    try:
        r = requests.get(info["video_url"], stream=True, timeout=30)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        # Schedule file deletion after 3 minutes
        schedule_file_deletion(filepath, delay=180)

        return jsonify({"download_url": f"/static/downloads/{filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

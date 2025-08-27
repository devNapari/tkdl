from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import tempfile
import os

app = Flask(__name__)

# ---- Inline frontend (index.html inside Python) ----
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TikTok Downloader</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      text-align: center;
      background: #fafafa;
      color: #111;
      transition: background 0.3s, color 0.3s;
    }
    body.dark {
      background: #121212;
      color: #f5f5f5;
    }
    .container {
      max-width: 600px;
      margin: 2rem auto;
      padding: 1rem;
    }
    h1 {
      color: #fe2c55;
      margin-bottom: 1rem;
    }
    #url {
      width: 100%;
      padding: 12px;
      margin-bottom: 1rem;
      border-radius: 8px;
      border: 1px solid #ccc;
      font-size: 16px;
    }
    button {
      background: #fe2c55;
      color: #fff;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 16px;
      margin: 5px;
    }
    button:hover { background: #e02548; }
    #preview-container {
      margin-top: 20px;
      display: flex;
      justify-content: center;
    }
    video, img {
      max-width: 100%;
      border-radius: 12px;
    }
    .spinner {
      border: 4px solid #f3f3f3;
      border-top: 4px solid #fe2c55;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 20px auto;
      display: none;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>TikTok Downloader</h1>
    <input type="text" id="url" placeholder="Paste TikTok URL here">
    <br>
    <button id="downloadBtn">Download</button>
    <button id="toggleTheme">Switch Theme</button>
    <div id="spinner" class="spinner"></div>
    <div id="preview-container"></div>
  </div>
  <script>
    const urlField = document.getElementById("url");
    const previewContainer = document.getElementById("preview-container");
    const downloadBtn = document.getElementById("downloadBtn");
    const spinner = document.getElementById("spinner");
    const toggleTheme = document.getElementById("toggleTheme");

    // Theme toggle
    toggleTheme.addEventListener("click", () => {
      document.body.classList.toggle("dark");
    });

    // Fetch preview
    async function fetchPreview() {
      if (!urlField.value) return;
      spinner.style.display = "block";
      previewContainer.innerHTML = "";
      try {
        const res = await fetch("/preview", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({url: urlField.value})
        });
        const data = await res.json();
        spinner.style.display = "none";
        if (data.error) {
          previewContainer.innerHTML = "<p style='color:red'>" + data.error + "</p>";
          return;
        }
        previewContainer.innerHTML = data.thumbnail
          ? `<img src="${data.thumbnail}">`
          : `<video src="${data.url}" controls muted></video>`;
      } catch (err) {
        spinner.style.display = "none";
        previewContainer.innerHTML = "<p style='color:red'>Could not load preview.</p>";
      }
    }

    urlField.addEventListener("change", fetchPreview);
    urlField.addEventListener("paste", () => setTimeout(fetchPreview, 100));

    // Download without leaving page
    downloadBtn.addEventListener("click", async () => {
      if (!urlField.value) return alert("Please enter a URL first.");
      const res = await fetch("/download", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({url: urlField.value})
      });
      if (!res.ok) return alert("Error downloading video");
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "tiktok.mp4";
      link.click();
    });
  </script>
</body>
</html>
"""

# ---- Backend logic ----

def extract_video_info(url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        video_url = None
        for f in formats:
            if f.get("ext") == "mp4" and f.get("url"):
                video_url = f["url"]
                break
        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "url": video_url
        }

@app.route("/")
def home():
    return render_template_string(INDEX_HTML)

@app.route("/preview", methods=["POST"])
def preview():
    data = request.get_json()
    url = data.get("url", "")
    try:
        info = extract_video_info(url)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url", "")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
        ydl_opts = {
            "quiet": True,
            "outtmpl": tmp_path
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(tmp_path, as_attachment=True, download_name="tiktok.mp4")
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    app.run(debug=True)

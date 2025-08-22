from flask import Flask, request, render_template, render_template_string, send_from_directory, redirect, url_for, flash

# Flask app version
import os
import requests
from yt_dlp import YoutubeDL
from TikTokApi import TikTokApi
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash
import asyncio

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flashing messages

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_with_ytdlp(url, output_dir):
    try:
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True, None
    except Exception as e:
        return False, str(e)

async def _download_with_tiktokapi_async(url, output_dir):
    api = TikTokApi()
    video = api.video(url=url)
    data = await video.bytes()
    filename = os.path.join(output_dir, 'tiktokapi_video.mp4')
    with open(filename, 'wb') as f:
        if isinstance(data, (bytes, bytearray, memoryview)):
            f.write(data)
        elif hasattr(data, "__aiter__"):
            async for chunk in data:
                f.write(chunk)
        else:
            raise TypeError("Unsupported data type returned by TikTokApi video.bytes()")
    return filename

def download_with_tiktokapi(url, output_dir):
    try:
        filename = asyncio.run(_download_with_tiktokapi_async(url, output_dir))
        return True, filename
    except Exception as e:
        return False, str(e)

def download_with_snaptik(url, output_dir):
    try:
        api_url = "https://snaptik.app/abc"  # Placeholder, real endpoint may differ
        resp = requests.post(api_url, data={'url': url})
        resp.raise_for_status()
        video_url = resp.json().get('video_url')
        if not video_url:
            raise Exception('No video URL found')
        video_data = requests.get(video_url).content
        filename = os.path.join(output_dir, 'snaptik_video.mp4')
        with open(filename, 'wb') as f:
            f.write(video_data)
        return True, filename
    except Exception as e:
        return False, str(e)

def try_download(url, output_dir=DOWNLOAD_DIR):
    # Try yt-dlp
    success, result = download_with_ytdlp(url, output_dir)
    if success:
        # Find the most recent file in output_dir
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
        latest_file = max(files, key=os.path.getctime)
        return True, latest_file, 'yt-dlp'
    # Try TikTokApi
    success, result = download_with_tiktokapi(url, output_dir)
    if success:
        return True, result, 'TikTokApi'
    # Try snaptik
    success, result = download_with_snaptik(url, output_dir)
    if success:
        return True, result, 'snaptik'
    return False, result, None



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            return render_template('index.html')
        success, result, method = try_download(url)
        if success:
            filename = os.path.basename(result)
            return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
        else:
            return render_template('index.html')
    return render_template('index.html')

@app.route('/downloads/<filename>')
def downloaded_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

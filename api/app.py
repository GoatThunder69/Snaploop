import requests
import json
import re
import time
from flask import Flask, jsonify, request

app = Flask(__name__)
@app.route("/health")
def health():
    return {"status": "ok"}
# ---------------- CONFIG ----------------
DEVELOPER = "@GoatThunder"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

# ---------------- CORE CLASS ----------------
class SnapchatProfileAPI:
    def __init__(self):
        self.headers = HEADERS

    def get_profile_picture_url(self, html, username):
        # og:image
        og = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html)
        if og:
            return og.group(1)

        # twitter:image
        tw = re.search(r'name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)', html)
        if tw:
            return tw.group(1)

        # fallback snapcode
        return f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG"

    def extract_snap_info(self, username):
        start = time.time()
        url = f"https://www.snapchat.com/add/{username}"

        try:
            r = requests.get(url, headers=self.headers, timeout=10)

            if r.status_code != 200:
                return {
                    "success": True,
                    "data": {
                        "username": username,
                        "exists": False,
                        "profile_url": url
                    },
                    "developer": DEVELOPER,
                    "response_time_ms": round((time.time() - start) * 1000, 2)
                }

            html = r.text

            data = {
                "username": username,
                "exists": True,
                "profile_url": url,
                "display_name": None,
                "description": None,
                "profile_picture_url": self.get_profile_picture_url(html, username),
                "snapcode_url": f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG",
                "subscriber_count": None,
                "location": None,
                "is_verified": "verified" in html.lower()
            }

            # Title → display name
            title = re.search(r'<title>(.*?)</title>', html)
            if title:
                data["display_name"] = title.group(1).strip()

            # Description
            desc = re.search(r'name=["\']description["\'][^>]*content=["\'](.*?)"', html)
            if desc:
                data["description"] = desc.group(1)

            # Subscribers
            if data["description"]:
                sub = re.search(r'(\d+(?:\.\d+)?k?)\s*subscribers', data["description"], re.I)
                if sub:
                    data["subscriber_count"] = sub.group(1)

                loc = re.search(r'📍\s*(.+)', data["description"])
                if loc:
                    data["location"] = loc.group(1)

            # remove None values
            data = {k: v for k, v in data.items() if v is not None}

            return {
                "success": True,
                "data": data,
                "developer": DEVELOPER,
                "response_time_ms": round((time.time() - start) * 1000, 2)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "developer": DEVELOPER
            }


snap_api = SnapchatProfileAPI()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return jsonify({
        "api": "Snapchat Profile API",
        "status": "running",
        "developer": DEVELOPER,
        "endpoints": {
            "/profile/<username>": "Full profile info",
            "/check/<username>": "Check if username exists",
            "/image/<username>": "Profile image only"
        }
    })


@app.route("/profile/<username>")
def profile(username):
    return jsonify(snap_api.extract_snap_info(username))


@app.route("/check/<username>")
def check(username):
    url = f"https://www.snapchat.com/add/{username}"
    try:
        r = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return jsonify({
            "success": True,
            "username": username,
            "exists": r.status_code == 200,
            "snapcode_url": f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG",
            "developer": DEVELOPER
        })
    except:
        return jsonify({
            "success": False,
            "username": username,
            "exists": False,
            "developer": DEVELOPER
        })


@app.route("/image/<username>")
def image(username):
    info = snap_api.extract_snap_info(username)

    if info["success"] and info["data"]["exists"]:
        return jsonify({
            "success": True,
            "username": username,
            "profile_picture_url": info["data"].get("profile_picture_url"),
            "snapcode_url": info["data"].get("snapcode_url"),
            "developer": DEVELOPER
        })

    return jsonify({
        "success": False,
        "username": username,
        "error": "Profile image not found",
        "developer": DEVELOPER
    })

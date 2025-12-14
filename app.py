import requests
import re
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

OWNER = "@GoatThunder"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

ALL_FIELDS = [
    "display_name",
    "description",
    "location",
    "website",
    "profile_picture_url",
    "bitmoji_url",
    "snapcode_url",
    "subscriber_count",
    "snap_score",
    "friend_count",
    "has_stories",
    "story_count",
    "is_verified",
    "profile_completeness_score"
]

def safe(primary, fallback=None):
    return primary if primary not in [None, "", "N/A"] else fallback

class SnapchatAPI:

    def get_profile_html(self, username):
        url = f"https://www.snapchat.com/add/{username}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.text if r.status_code == 200 else None

    def get_story_html(self, username):
        url = f"https://story.snapchat.com/@{username}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.text if r.status_code == 200 else None

    def extract(self, username):
        start = time.time()

        data = {
            "username": username,
            "exists": False
        }

        html = self.get_profile_html(username)
        story_html = self.get_story_html(username)

        if html:
            data["exists"] = True

            title = re.search(r"<title>(.*?)</title>", html)
            data["display_name"] = title.group(1).strip() if title else None

            desc = re.search(r'name="description" content="(.*?)"', html)
            data["description"] = desc.group(1) if desc else None

            og = re.search(r'property="og:image" content="(.*?)"', html)
            data["profile_picture_url"] = og.group(1) if og else None

            if data["description"]:
                loc = re.search(r"📍\s*(.+)", data["description"])
                data["location"] = loc.group(1) if loc else None

        if story_html:
            data["has_stories"] = True
            data["story_count"] = len(re.findall("story", story_html))
            if not data.get("profile_picture_url"):
                img = re.search(r'<img[^>]+src="([^"]+)"', story_html)
                data["profile_picture_url"] = img.group(1) if img else None
        else:
            data["has_stories"] = False
            data["story_count"] = 0

        data["snapcode_url"] = f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=PNG"

        score = 0
        if data.get("display_name"): score += 20
        if data.get("profile_picture_url"): score += 25
        if data.get("description"): score += 15
        if data.get("has_stories"): score += 10
        data["profile_completeness_score"] = score

        # Ensure ALL fields exist
        for f in ALL_FIELDS:
            data.setdefault(f, None)

        return {
            "success": True,
            "data": data,
            "Owner": OWNER,
            "response_time_ms": round((time.time() - start) * 1000, 2)
        }

snap = SnapchatAPI()

# ---------------- ROUTES ----------------

@app.route("/health")
def health():
    return {"status": "ok", "Owner": OWNER}

@app.route("/")
def home():
    return {
        "api": "Snapchat Full Feature API",
        "status": "running",
        "Owner": OWNER
    }

@app.route("/profile/<username>")
def profile(username):
    return jsonify(snap.extract(username))

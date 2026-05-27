from flask import Flask, request, jsonify
import requests
import json
import os
import re
import tempfile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

ZEPH_KEY = "ZEPH-ZRJD1U"

# Safe temp stats file for Vercel
STATS_FILE = os.path.join(
    tempfile.gettempdir(),
    "stats.json"
)

# Session + Retry
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


# ---------------- STATS ----------------

def default_stats():
    return {
        "total_hits": 0,
        "last_hit_ip": "",
        "ip_hits": {}
    }


def load_stats():
    try:
        if not os.path.exists(STATS_FILE):
            return default_stats()

        with open(STATS_FILE, "r") as f:
            return json.load(f)

    except:
        return default_stats()


def save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except:
        pass


def update_stats(ip):
    stats = load_stats()

    stats["total_hits"] += 1
    stats["last_hit_ip"] = ip

    if ip not in stats["ip_hits"]:
        stats["ip_hits"][ip] = 0

    stats["ip_hits"][ip] += 1

    save_stats(stats)


# ---------------- CLEAN ----------------

def clean_data(data):

    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [clean_data(i) for i in data]

    elif isinstance(data, str):
        # Remove @anything
        return re.sub(r'@\S+', '', data)

    return data


# ---------------- VEHICLE API ----------------

@app.route("/api/vehicle", methods=["GET"])
def vehicle():

    number = request.args.get("number")

    if not number:
        return jsonify({
            "success": False,
            "error": "number parameter missing"
        }), 400

    number = number.upper().replace(" ", "")

    # Real visitor IP
    ip = request.headers.get(
        "x-forwarded-for",
        request.remote_addr
    )

    if "," in ip:
        ip = ip.split(",")[0].strip()

    try:
        update_stats(ip)
    except:
        pass

    api1 = (
        f"https://www.zephrexdigital.site/api?"
        f"key={ZEPH_KEY}&type=VNUM&term={number}"
    )

    api2 = (
        f"https://vehicle-infox.profilework239.workers.dev/"
        f"?number={number}"
    )

    merged_data = {}

    # API1
    try:
        r1 = session.get(api1, timeout=15)
        d1 = clean_data(r1.json())

        if isinstance(d1, dict):
            if "data" in d1 and isinstance(d1["data"], dict):
                merged_data.update(d1["data"])
            else:
                merged_data.update(d1)

    except:
        pass

    # API2
    try:
        r2 = session.get(api2, timeout=15)
        d2 = clean_data(r2.json())

        if isinstance(d2, dict):
            if "data" in d2 and isinstance(d2["data"], dict):
                merged_data.update(d2["data"])
            else:
                merged_data.update(d2)

    except:
        pass

    return jsonify({
        "success": True,
        "regn_no": number,
        "data": merged_data
    })


# ---------------- STATS API ----------------

@app.route("/api/stats", methods=["GET"])
def stats():

    stats = load_stats()

    top_ips = dict(
        sorted(
            stats["ip_hits"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
    )

    return jsonify({
        "total_hits": stats["total_hits"],
        "unique_ips": len(stats["ip_hits"]),
        "last_hit_ip": stats["last_hit_ip"],
        "top_ips": top_ips,
        "all_ip_hits": stats["ip_hits"]
    })


if __name__ == "__main__":
    app.run(debug=True)

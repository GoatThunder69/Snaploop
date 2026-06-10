from flask import Flask, request, jsonify
import requests
import re
import os
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from redis import Redis

app = Flask(__name__)

# Redis
redis = Redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True
)

# Session
session = requests.Session()

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


# -------- CLEAN --------
REMOVE_KEYS = {
    "developer",
    "developer_by",
    "credit",
    "credits",
    "req_total",
    "@",
    "req_total",
    "total_left",
    "left"
}

def clean_data(data):

    if isinstance(data, dict):

        cleaned = {}

        for k, v in data.items():

            key_lower = str(k).lower().strip()

            if key_lower in REMOVE_KEYS:
                continue

            cleaned[k] = clean_data(v)

        return cleaned

    elif isinstance(data, list):
        return [clean_data(i) for i in data]

    elif isinstance(data, str):
        return re.sub(r'@\S+', '', data)

    return data


# -------- STATS --------
def update_stats(ip):

    redis.incr("total_hits")
    redis.set("last_hit_ip", ip)
    redis.hincrby("ip_hits", ip, 1)


@app.route("/api/stats", methods=["GET"])
def stats():

    total_hits = int(
        redis.get("total_hits") or 0
    )

    last_hit_ip = (
        redis.get("last_hit_ip") or ""
    )

    ip_hits = (
        redis.hgetall("ip_hits") or {}
    )

    top_ips = dict(
        sorted(
            ip_hits.items(),
            key=lambda x: int(x[1]),
            reverse=True
        )[:10]
    )

    return jsonify({
        "total_hits": total_hits,
        "unique_ips": len(ip_hits),
        "last_hit_ip": last_hit_ip,
        "top_ips": top_ips,
        "all_ip_hits": ip_hits
    })


# -------- VEHICLE --------
@app.route("/api/vehicle", methods=["GET"])
def vehicle():

    number = request.args.get("number")

    if not number:
        return jsonify({
            "success": False,
            "error": "number parameter missing"
        }), 400

    number = (
        number.upper()
        .replace(" ", "")
    )

    ip = request.headers.get(
        "x-forwarded-for",
        request.remote_addr
    )

    if "," in ip:
        ip = ip.split(",")[0].strip()

    # Stats same safe
    try:
        update_stats(ip)
    except:
        pass

    # Cache same
    cache_key = f"vehicle:v2:{number}"

    try:
        cached = redis.get(cache_key)

        if cached:
            return jsonify(
                json.loads(cached)
            )
    except:
        pass

    # # API1
api1 = (
    f"https://v2iop-panel.vercel.app/api/mera"
    f"?query={number}"
)

# API2
api2 = (
    f"https://v2iop-panel.vercel.app/api/mera2"
    f"?query={number}"
    )

    merged_data = {}

    # API1
    try:
        r1 = session.get(
            api1,
            timeout=15
        )

        d1 = clean_data(
            r1.json()
        )

        if isinstance(d1, dict):

            if (
                "data" in d1 and
                isinstance(d1["data"], dict)
            ):
                merged_data.update(
                    d1["data"]
                )
            else:
                merged_data.update(d1)

    except:
        pass

    # API2
    try:
        r2 = session.get(
            api2,
            timeout=15
        )

        d2 = clean_data(
            r2.json()
        )

        if isinstance(d2, dict):

            if (
                "data" in d2 and
                isinstance(d2["data"], dict)
            ):
                merged_data.update(
                    d2["data"]
                )
            else:
                merged_data.update(d2)

    except:
        pass

    response_data = {
        "success": True,
        "regn_no": number,
        "data": merged_data
    }

    # Cache 3600 same
    try:
        redis.setex(
            cache_key,
            3600,
            json.dumps(response_data)
        )
    except:
        pass

    return jsonify(response_data)


@app.route("/")
def home():
    return jsonify({
        "status": "online"
    })


if __name__ == "__main__":
    app.run(debug=True)

export default async function handler(req, res) {
  const mobile = req.query.mobile;

  if (!mobile) {
    return res.status(400).json({
      status: false,
      message: "mobile parameter missing"
    });
  }

  const apiUrl =
    "https://num.proportalxc.workers.dev/?mobile=" +
    encodeURIComponent(mobile);

  try {
    const response = await fetch(apiUrl, {
      headers: {
        "User-Agent": "Mozilla/5.0"
      }
    });

    const data = await response.json(); // JSON response

    // 🔐 Recursive cleaner
    const clean = (v) => {
      if (typeof v === "string") {
        return v
          .replace(/https?:\/\/\S+/gi, "[hidden]")
          .replace(/@\S+/g, "[hidden]");
      }
      if (Array.isArray(v)) return v.map(clean);
      if (typeof v === "object" && v !== null) {
        const o = {};
        for (const k in v) o[k] = clean(v[k]);
        return o;
      }
      return v;
    };

    res.setHeader("Content-Type", "application/json");
    res.status(200).json(clean(data));

  } catch (err) {
    res.status(500).json({
      status: false,
      error: "API fetch failed"
    });
  }
    }

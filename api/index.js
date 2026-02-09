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
      headers: { "User-Agent": "Mozilla/5.0" }
    });

    const raw = await response.json();

    // 🔐 clean text
    const cleanText = (v) => {
      if (typeof v !== "string") return v;
      return v
        .replace(/https?:\/\/\S+/gi, "")
        .replace(/@\S+/g, "")
        .trim();
    };

    // 🔍 deep search in JSON
    const found = {};

    const search = (obj) => {
      if (Array.isArray(obj)) {
        obj.forEach(search);
      } else if (obj && typeof obj === "object") {
        for (const k in obj) {
          const key = k.toLowerCase();
          const val = obj[k];

          if (typeof val === "string") {
            if (!found.Name && key.includes("name") && !key.includes("father")) {
              found.Name = cleanText(val);
            }
            if (!found.FName && (key.includes("father") || key.includes("fname"))) {
              found.FName = cleanText(val);
            }
            if (!found.ID_Number && (key.includes("id") || key.includes("aadhaar") || key.includes("pan"))) {
              found.ID_Number = cleanText(val);
            }
            if (!found.Alt_Number && (key.includes("alt") || key.includes("secondary"))) {
              found.Alt_Number = cleanText(val);
            }
            if (!found.Address && (key.includes("address") || key.includes("location"))) {
              found.Address = cleanText(val);
            }
          }

          if (typeof val === "object") {
            search(val);
          }
        }
      }
    };

    search(raw);

    res.status(200).json({
      status: true,
      data: found,
      raw_available: Object.keys(found).length > 0
    });

  } catch (err) {
    res.status(500).json({
      status: false,
      error: "API fetch failed"
    });
  }
}

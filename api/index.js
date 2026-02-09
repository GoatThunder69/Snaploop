export default async function handler(req, res) {
  const term = req.query.term;

  if (!term) {
    return res.status(400).json({
      status: false,
      message: "term parameter missing"
    });
  }

  const apiUrl =
    "https://api.subhxcosmo.in/api?key=VNIOX&type=mobile&term=" +
    encodeURIComponent(term);

  try {
    const r = await fetch(apiUrl, {
      headers: {
        "User-Agent": "Mozilla/5.0"
      }
    });

    let data = await r.json(); // ✅ JSON response

    // 🔥 Recursive cleaner (JSON ke andar kahin bhi ho)
    const cleanData = (obj) => {
      if (typeof obj === "string") {
        return obj
          // hide https/http links
          .replace(/https?:\/\/\S+/gi, "[hidden]")
          // hide @mentions like @Stark, @anything
          .replace(/@\S+/g, "[hidden]");
      }

      if (Array.isArray(obj)) {
        return obj.map(cleanData);
      }

      if (typeof obj === "object" && obj !== null) {
        const cleaned = {};
        for (const key in obj) {
          cleaned[key] = cleanData(obj[key]);
        }
        return cleaned;
      }

      return obj;
    };

    const cleanedResponse = cleanData(data);

    res.setHeader("Content-Type", "application/json");
    res.status(200).json(cleanedResponse);

  } catch (err) {
    res.status(500).json({
      status: false,
      error: "API fetch failed"
    });
  }
}

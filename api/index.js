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

    // 🔐 hide links + @mentions
    const sanitize = (v) => {
      if (typeof v === "string") {
        return v
          .replace(/https?:\/\/\S+/gi, "")
          .replace(/@\S+/g, "")
          .trim();
      }
      return v;
    };

    // 🧠 FIELD MAPPING (safe fallback)
    const result = {
      Name: sanitize(
        raw.name || raw.Name || raw.owner || raw.full_name || "N/A"
      ),
      FName: sanitize(
        raw.father_name || raw.fname || raw.FName || "N/A"
      ),
      ID_Number: sanitize(
        raw.id || raw.id_number || raw.aadhaar || raw.pan || "N/A"
      ),
      Alt_Number: sanitize(
        raw.alt || raw.alt_number || raw.secondary || "N/A"
      ),
      Address: sanitize(
        raw.address || raw.Address || raw.location || "N/A"
      )
    };

    res.status(200).json({
      status: true,
      data: result
    });

  } catch (err) {
    res.status(500).json({
      status: false,
      error: "API fetch or parse failed"
    });
  }
        }

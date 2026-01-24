import express from "express";
import fetch from "node-fetch";

const app = express();
app.use(express.json());

app.post("/renovate", async (req, res) => {
  try {
    const {
      repository,
      prTitle,
      prUrl,
      depName,
      currentVersion,
      newVersion,
      datasource,
    } = req.body;

    const embed = {
      title: "Renovate opened a PR",
      url: prUrl,
      color: 0x1abc9c,
      fields: [
        { name: "Repository", value: repository, inline: true },
        { name: "Dependency", value: depName || "multiple", inline: true },
        {
          name: "Version",
          value: currentVersion && newVersion
            ? `${currentVersion} → ${newVersion}`
            : "see PR",
          inline: true,
        },
        { name: "Datasource", value: datasource || "unknown", inline: true },
      ],
      footer: {
        text: "Renovate Bot",
      },
      timestamp: new Date().toISOString(),
    };

    await fetch(process.env.DISCORD_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ embeds: [embed] }),
    });

    res.sendStatus(204);
  } catch (err) {
    console.error(err);
    res.sendStatus(500);
  }
});

app.listen(3000, () =>
  console.log("Renovate Discord relay listening on :3000")
);

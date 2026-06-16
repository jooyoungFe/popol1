const token = "urtoken";
const headers = {
  Authorization: token,
  "Content-Type": "application/json",
};

const guilds = ["1385646193773903933", "1267560027749613688"]; 
const delayMs = 3000;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function run() {
  while (true) {
    for (const guildId of guilds) {
      const payload = {
        identity_guild_id: guildId,
        identity_enabled: true,
      };


      try {
        const res = await fetch("https://discord.com/api/v9/users/@me/settings", { 
          method: "PUT", 
          headers, 
          body: JSON.stringify(payload), 
        });

        const text = await res.text();
        console.log(`[${guildId}] ${res.status} ${res.statusText}`);
        console.log(text.slice(0, 500));
        console.log("x-ratelimit-remaining:", res.headers.get("x-ratelimit-remaining"));
        console.log("x-ratelimit-reset-after:", res.headers.get("x-ratelimit-reset-after"));

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
      } catch (e) {
        console.error(`[${guildId}] 요청 실패:`, e);
      }

       
 
      await sleep(delayMs);
    }
  }
}

run().catch(console.error);

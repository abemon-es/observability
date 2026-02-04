#!/usr/bin/env node
const { io } = require("socket.io-client");

const UPTIME_KUMA_URL = "https://status.abemon.es";
const USERNAME = process.env.UPTIME_USER;
const PASSWORD = process.env.UPTIME_PASS;

const STATUS_PAGE_GROUPS = [
  { name: "SSL Certificates", monitors: ["abemon.es SSL", "bm.consulting SSL", "foodplan.pro SSL", "blue-mountain.es SSL", "codex.abemon.es SSL", "logisticsexpress.es SSL", "concursal.consulting SSL", "status.abemon.es SSL", "logs.abemon.es SSL", "pricing.logisticsexpress.es SSL"] },
  { name: "DNS Resolution", monitors: ["abemon.es DNS", "bm.consulting DNS", "foodplan.pro DNS", "codex.abemon.es DNS", "logisticsexpress.es DNS", "blue-mountain.es DNS"] },
  { name: "WordPress Sites", monitors: ["abemon.es", "bm.consulting", "codex.abemon.es", "blue-mountain.es"] },
  { name: "Apps & APIs", monitors: ["foodplan.pro", "api-pricing"] },
  { name: "Observability", monitors: ["Grafana", "Loki"] }
];

const socket = io(UPTIME_KUMA_URL, { transports: ["websocket"] });

socket.on("connect", async () => {
  console.log("[OK] Connected");

  // Login
  socket.emit("login", { username: USERNAME, password: PASSWORD, token: "" }, async (res) => {
    if (!res.ok) { console.error("Login failed"); process.exit(1); }
    console.log("[OK] Logged in");

    // Wait for monitor list
    await new Promise(r => setTimeout(r, 1000));

    socket.once("monitorList", (monitors) => {
      const monitorMap = {};
      Object.values(monitors).forEach(m => monitorMap[m.name] = m.id);
      console.log(`[OK] ${Object.keys(monitorMap).length} monitors`);

      // Get status page
      socket.emit("getStatusPage", "main", (res) => {
        if (!res.ok) { console.error("Failed to get page"); process.exit(1); }
        console.log("[OK] Got status page");

        const config = res.config;
        const existingGroups = res.publicGroupList || [];
        
        // Keep groups not in our list
        const ourGroupNames = STATUS_PAGE_GROUPS.map(g => g.name);
        const keepGroups = existingGroups.filter(g => !ourGroupNames.includes(g.name));

        // Build new groups
        const newGroups = [...keepGroups];
        let weight = keepGroups.length + 1;

        for (const group of STATUS_PAGE_GROUPS) {
          const monitorList = group.monitors
            .filter(name => monitorMap[name])
            .map(name => ({ id: monitorMap[name] }));
          
          if (monitorList.length > 0) {
            newGroups.push({ name: group.name, weight: weight++, monitorList });
            console.log(`[OK] ${group.name}: ${monitorList.length} monitors`);
          }
        }

        // Save - pass icon as empty string instead of null
        socket.emit("saveStatusPage", "main", config, "", newGroups, (res) => {
          if (res.ok) {
            console.log("\n[SUCCESS] Status page updated!");
            console.log(`Total groups: ${newGroups.length}`);
          } else {
            console.error("[ERROR]", res.msg);
          }
          socket.disconnect();
          process.exit(res.ok ? 0 : 1);
        });
      });
    });

    socket.emit("getMonitorList");
  });
});

socket.on("connect_error", (e) => { console.error("Connection failed:", e.message); process.exit(1); });
setTimeout(() => { console.error("Timeout"); process.exit(1); }, 60000);

#!/usr/bin/env node
/**
 * List all monitors in Uptime Kuma
 *
 * Usage:
 *   UPTIME_USER=xxx UPTIME_PASS=xxx node list-monitors.js
 */

const { io } = require("socket.io-client");

const UPTIME_KUMA_URL = process.env.UPTIME_KUMA_URL || "https://status.abemon.es";
const USERNAME = process.env.UPTIME_USER;
const PASSWORD = process.env.UPTIME_PASS;

if (!USERNAME || !PASSWORD) {
  console.error("Error: Set UPTIME_USER and UPTIME_PASS environment variables");
  process.exit(1);
}

function createSocket() {
  return io(UPTIME_KUMA_URL, {
    transports: ["websocket"],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
  });
}

async function main() {
  console.log("Connecting to Uptime Kuma at", UPTIME_KUMA_URL);

  const socket = createSocket();

  const overallTimeout = setTimeout(() => {
    console.error("[ERROR] Timeout. Exiting.");
    socket.disconnect();
    process.exit(1);
  }, 30000);

  socket.on("connect", () => {
    console.log("[OK] Connected\n");

    socket.emit("login", {
      username: USERNAME,
      password: PASSWORD,
      token: "",
    }, (response) => {
      if (!response.ok) {
        console.error("[ERROR] Login failed:", response.msg);
        clearTimeout(overallTimeout);
        socket.disconnect();
        process.exit(1);
      }
      console.log("[OK] Logged in\n");
    });
  });

  // Listen for monitor list
  socket.on("monitorList", (monitors) => {
    console.log("=== Current Monitors ===\n");

    const monitorArray = Object.values(monitors);
    monitorArray.sort((a, b) => a.id - b.id);

    for (const m of monitorArray) {
      console.log(`ID: ${m.id} | Type: ${m.type} | Name: ${m.name}`);
      if (m.url) console.log(`   URL: ${m.url}`);
      if (m.hostname) console.log(`   Hostname: ${m.hostname}`);
      console.log(`   Active: ${m.active}`);
      console.log("");
    }

    console.log(`Total: ${monitorArray.length} monitors`);

    clearTimeout(overallTimeout);
    socket.disconnect();
    process.exit(0);
  });

  socket.on("connect_error", (error) => {
    console.error("[ERROR] Connection failed:", error.message);
    clearTimeout(overallTimeout);
    process.exit(1);
  });
}

main();

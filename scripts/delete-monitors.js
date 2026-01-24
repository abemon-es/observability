#!/usr/bin/env node
/**
 * Delete specific monitors from Uptime Kuma
 *
 * Usage:
 *   UPTIME_USER=xxx UPTIME_PASS=xxx node delete-monitors.js 11 16 17 18 19
 */

const { io } = require("socket.io-client");

const UPTIME_KUMA_URL = process.env.UPTIME_KUMA_URL || "https://status.abemon.es";
const USERNAME = process.env.UPTIME_USER;
const PASSWORD = process.env.UPTIME_PASS;

if (!USERNAME || !PASSWORD) {
  console.error("Error: Set UPTIME_USER and UPTIME_PASS environment variables");
  process.exit(1);
}

// Get monitor IDs from command line
const monitorIdsToDelete = process.argv.slice(2).map(id => parseInt(id, 10));

if (monitorIdsToDelete.length === 0) {
  console.log("Usage: UPTIME_USER=xxx UPTIME_PASS=xxx node delete-monitors.js <id1> <id2> ...");
  console.log("Example: UPTIME_USER=xxx UPTIME_PASS=xxx node delete-monitors.js 11 16 17 18 19");
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

function withTimeout(promise, ms, name) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms for ${name}`)), ms)
    ),
  ]);
}

function login(socket) {
  return new Promise((resolve, reject) => {
    socket.emit("login", {
      username: USERNAME,
      password: PASSWORD,
      token: "",
    }, (response) => {
      if (response.ok) {
        console.log("[OK] Logged in");
        resolve(response);
      } else {
        reject(new Error(`Login failed: ${response.msg}`));
      }
    });
  });
}

function deleteMonitor(socket, id) {
  return new Promise((resolve, reject) => {
    socket.emit("deleteMonitor", id, (response) => {
      if (response.ok) {
        console.log(`[OK] Deleted monitor ID: ${id}`);
        resolve(response);
      } else {
        reject(new Error(`Failed to delete ${id}: ${response.msg}`));
      }
    });
  });
}

async function main() {
  console.log("Connecting to Uptime Kuma at", UPTIME_KUMA_URL);
  console.log("Monitors to delete:", monitorIdsToDelete.join(", "));
  console.log("");

  const socket = createSocket();

  const overallTimeout = setTimeout(() => {
    console.error("[ERROR] Timeout. Exiting.");
    socket.disconnect();
    process.exit(1);
  }, 60000);

  socket.on("connect", async () => {
    console.log("[OK] Connected");

    try {
      await withTimeout(login(socket), 10000, "login");

      console.log("\n--- Deleting Monitors ---");
      let deleted = 0;
      let failed = 0;

      for (const id of monitorIdsToDelete) {
        try {
          await withTimeout(deleteMonitor(socket, id), 10000, `delete-${id}`);
          deleted++;
        } catch (error) {
          console.error(`[ERROR] ${error.message}`);
          failed++;
        }
      }

      console.log(`\n=== Summary ===`);
      console.log(`Deleted: ${deleted}`);
      console.log(`Failed: ${failed}`);

      clearTimeout(overallTimeout);
      socket.disconnect();
      process.exit(0);

    } catch (error) {
      console.error("[ERROR]", error.message);
      clearTimeout(overallTimeout);
      socket.disconnect();
      process.exit(1);
    }
  });

  socket.on("connect_error", (error) => {
    console.error("[ERROR] Connection failed:", error.message);
    clearTimeout(overallTimeout);
    process.exit(1);
  });
}

main();

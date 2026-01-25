#!/usr/bin/env node
/**
 * Add SSL and DNS monitors to Uptime Kuma
 * Uses Socket.IO to connect and add monitors programmatically
 *
 * Usage:
 *   UPTIME_USER=xxx UPTIME_PASS=xxx node add-ssl-dns-monitors.js
 *
 * Or create .env file with UPTIME_USER and UPTIME_PASS
 */

const { io } = require("socket.io-client");

// Configuration
const UPTIME_KUMA_URL = process.env.UPTIME_KUMA_URL || "https://status.abemon.es";
const USERNAME = process.env.UPTIME_USER;
const PASSWORD = process.env.UPTIME_PASS;
const NOTIFICATION_ID = parseInt(process.env.NOTIFICATION_ID || "1", 10);

if (!USERNAME || !PASSWORD) {
  console.error("Error: Set UPTIME_USER and UPTIME_PASS environment variables");
  console.log("Usage: UPTIME_USER=xxx UPTIME_PASS=xxx node add-ssl-dns-monitors.js");
  process.exit(1);
}

// SSL Certificate monitors - Using HTTP type with SSL certificate check enabled
const SSL_MONITORS = [
  { name: "abemon.es SSL", url: "https://abemon.es" },
  { name: "bm.consulting SSL", url: "https://bm.consulting" },
  { name: "foodplan.pro SSL", url: "https://foodplan.pro" },
  { name: "blue-mountain.es SSL", url: "https://blue-mountain.es" },
  { name: "codex.abemon.es SSL", url: "https://codex.abemon.es" },
  { name: "logisticsexpress.es SSL", url: "https://logisticsexpress.es" },
  { name: "concursal.consulting SSL", url: "https://concursal.consulting" },
  { name: "status.abemon.es SSL", url: "https://status.abemon.es" },
  { name: "logs.abemon.es SSL", url: "https://logs.abemon.es" },
  { name: "pricing.logisticsexpress.es SSL", url: "https://pricing.logisticsexpress.es" },
];

// DNS monitors - Check A record resolution
const DNS_MONITORS = [
  { name: "abemon.es DNS", hostname: "abemon.es" },
  { name: "bm.consulting DNS", hostname: "bm.consulting" },
  { name: "foodplan.pro DNS", hostname: "foodplan.pro" },
  { name: "codex.abemon.es DNS", hostname: "codex.abemon.es" },
  { name: "logisticsexpress.es DNS", hostname: "logisticsexpress.es" },
  { name: "blue-mountain.es DNS", hostname: "blue-mountain.es" },
];

// HTTP Health monitors - Check service availability
const HTTP_MONITORS = [
  { name: "abemon.es", url: "https://abemon.es", group: "WordPress Sites" },
  { name: "bm.consulting", url: "https://bm.consulting", group: "WordPress Sites" },
  { name: "codex.abemon.es", url: "https://codex.abemon.es", group: "WordPress Sites" },
  { name: "blue-mountain.es", url: "https://blue-mountain.es", group: "WordPress Sites" },
  { name: "foodplan.pro", url: "https://foodplan.pro", group: "Apps" },
  { name: "api-pricing", url: "https://pricing.logisticsexpress.es/api/v1/territories", group: "APIs" },
  { name: "Grafana", url: "https://logs.abemon.es/api/health", group: "Observability" },
  { name: "Loki", url: "https://loki-production-f8e1.up.railway.app/ready", group: "Observability" },
];

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
        console.log("[OK] Logged in successfully");
        resolve(response);
      } else {
        reject(new Error(`Login failed: ${response.msg}`));
      }
    });
  });
}

function addMonitor(socket, monitor) {
  return new Promise((resolve, reject) => {
    socket.emit("add", monitor, (response) => {
      if (response.ok) {
        console.log(`[OK] Added monitor: ${monitor.name} (ID: ${response.monitorID})`);
        resolve(response);
      } else {
        // Check if monitor already exists
        if (response.msg && response.msg.includes("UNIQUE constraint failed")) {
          console.log(`[SKIP] Monitor already exists: ${monitor.name}`);
          resolve({ ok: true, skipped: true });
        } else {
          reject(new Error(`Failed to add ${monitor.name}: ${response.msg}`));
        }
      }
    });
  });
}

async function addSSLMonitors(socket) {
  console.log("\n--- Adding SSL Certificate Monitors ---");
  let added = 0;
  let skipped = 0;

  for (const ssl of SSL_MONITORS) {
    try {
      const monitor = {
        type: "http",
        name: ssl.name,
        url: ssl.url,
        method: "GET",
        interval: 300, // Check every 5 minutes
        retryInterval: 60,
        resendInterval: 0,
        maxretries: 3,
        timeout: 30,
        expiryNotification: true,    // Enable SSL certificate expiry check
        ignoreTls: false,            // Don't ignore TLS errors
        accepted_statuscodes: ["200-299", "301", "302"],
        notificationIDList: { [NOTIFICATION_ID]: true },
        active: true,
      };

      const response = await withTimeout(addMonitor(socket, monitor), 10000, ssl.name);
      if (response.skipped) {
        skipped++;
      } else {
        added++;
      }
    } catch (error) {
      console.error(`[ERROR] ${ssl.name}: ${error.message}`);
    }
  }

  return { added, skipped };
}

async function addDNSMonitors(socket) {
  console.log("\n--- Adding DNS Monitors ---");
  let added = 0;
  let skipped = 0;

  for (const dns of DNS_MONITORS) {
    try {
      const monitor = {
        type: "dns",
        name: dns.name,
        hostname: dns.hostname,
        port: 53,                       // DNS port
        dns_resolve_type: "A",          // Check A record
        dns_resolve_server: "1.1.1.1",  // Use Cloudflare DNS
        interval: 300,                  // Check every 5 minutes
        retryInterval: 60,
        resendInterval: 0,
        maxretries: 3,
        timeout: 30,
        accepted_statuscodes: [],       // Required but empty for DNS
        notificationIDList: { [NOTIFICATION_ID]: true },
        active: true,
      };

      const response = await withTimeout(addMonitor(socket, monitor), 10000, dns.name);
      if (response.skipped) {
        skipped++;
      } else {
        added++;
      }
    } catch (error) {
      console.error(`[ERROR] ${dns.name}: ${error.message}`);
    }
  }

  return { added, skipped };
}

async function addHTTPMonitors(socket) {
  console.log("\n--- Adding HTTP Health Monitors ---");
  let added = 0;
  let skipped = 0;

  for (const http of HTTP_MONITORS) {
    try {
      const monitor = {
        type: "http",
        name: http.name,
        url: http.url,
        method: "GET",
        interval: 60,                   // Check every minute
        retryInterval: 30,
        resendInterval: 0,
        maxretries: 3,
        timeout: 30,
        expiryNotification: false,
        ignoreTls: false,
        accepted_statuscodes: ["200-299"],
        notificationIDList: { [NOTIFICATION_ID]: true },
        active: true,
      };

      const response = await withTimeout(addMonitor(socket, monitor), 10000, http.name);
      if (response.skipped) {
        skipped++;
      } else {
        added++;
      }
    } catch (error) {
      console.error(`[ERROR] ${http.name}: ${error.message}`);
    }
  }

  return { added, skipped };
}

async function main() {
  console.log("Connecting to Uptime Kuma at", UPTIME_KUMA_URL);

  const socket = createSocket();

  // Set overall timeout
  const overallTimeout = setTimeout(() => {
    console.error("\n[ERROR] Overall timeout reached (60s). Exiting.");
    socket.disconnect();
    process.exit(1);
  }, 60000);

  socket.on("connect", async () => {
    console.log("[OK] Connected to Uptime Kuma");

    try {
      await withTimeout(login(socket), 10000, "login");

      // Add all monitors
      const sslResult = await addSSLMonitors(socket);
      const dnsResult = await addDNSMonitors(socket);
      const httpResult = await addHTTPMonitors(socket);

      console.log("\n=== Summary ===");
      console.log(`SSL monitors: ${sslResult.added} added, ${sslResult.skipped} skipped`);
      console.log(`DNS monitors: ${dnsResult.added} added, ${dnsResult.skipped} skipped`);
      console.log(`HTTP monitors: ${httpResult.added} added, ${httpResult.skipped} skipped`);
      console.log(`Notification linked: ID ${NOTIFICATION_ID}`);
      console.log("\nMonitors should now appear on the status page.");

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

  socket.on("disconnect", (reason) => {
    console.log("[INFO] Disconnected:", reason);
  });
}

main();

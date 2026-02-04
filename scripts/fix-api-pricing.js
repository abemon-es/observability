const { io } = require("socket.io-client");
const socket = io("https://status.abemon.es", { transports: ["websocket"] });

socket.on("connect", () => {
  socket.emit("login", { username: process.env.UPTIME_USER, password: process.env.UPTIME_PASS, token: "" }, (res) => {
    if (!res.ok) { console.error("Login failed"); process.exit(1); }
    
    // Edit monitor ID 127 (api-pricing) to use root URL
    socket.emit("editMonitor", {
      id: 127,
      type: "http",
      name: "api-pricing",
      url: "https://pricing.logisticsexpress.es/",
      method: "GET",
      interval: 60,
      retryInterval: 30,
      maxretries: 3,
      timeout: 30,
      accepted_statuscodes: ["200-299"],
      active: true
    }, (res) => {
      if (res.ok) {
        console.log("[OK] Updated api-pricing monitor to use root URL");
      } else {
        console.error("[ERROR]", res.msg);
      }
      socket.disconnect();
      process.exit(0);
    });
  });
});

setTimeout(() => process.exit(1), 30000);

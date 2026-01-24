FROM louislam/uptime-kuma:1

# Custom branding will be applied via UI settings
# Logo and CSS injected through Uptime Kuma's built-in customization

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
  CMD node extra/healthcheck.js || exit 1

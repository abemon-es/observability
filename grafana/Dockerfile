FROM grafana/grafana:latest

USER root

# Copy provisioning configs
COPY provisioning /etc/grafana/provisioning
COPY grafana.ini /etc/grafana/grafana.ini

# Copy branding assets
COPY branding/logo.svg /usr/share/grafana/public/img/grafana_icon.svg
COPY branding/favicon.ico /usr/share/grafana/public/img/fav32.png

# Copy custom CSS for abemon.es branding
COPY branding/custom.css /usr/share/grafana/public/css/custom.css

# Inject custom CSS into Grafana's index.html
RUN sed -i 's|</head>|<link rel="stylesheet" href="/public/css/custom.css" /></head>|' /usr/share/grafana/public/views/index.html || true

# Copy entrypoint script that resets admin password
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Keep as root so we can reset password
# /run.sh will drop privileges properly

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]

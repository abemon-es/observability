FROM grafana/grafana:latest

USER root

# Copy provisioning configs
COPY provisioning /etc/grafana/provisioning
COPY grafana.ini /etc/grafana/grafana.ini

# Copy branding assets
COPY branding/logo.svg /usr/share/grafana/public/img/grafana_icon.svg
COPY branding/favicon.ico /usr/share/grafana/public/img/fav32.png

USER grafana

EXPOSE 3000

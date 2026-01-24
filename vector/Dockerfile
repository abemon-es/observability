FROM timberio/vector:latest-alpine

COPY vector.toml /etc/vector/vector.toml

# Vector API port
EXPOSE 8686
# HTTP log receiver port
EXPOSE 8080

ENV PORT=8080

CMD ["vector", "--config", "/etc/vector/vector.toml"]

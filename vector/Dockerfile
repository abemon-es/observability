FROM timberio/vector:latest-alpine

COPY vector.toml /etc/vector/vector.toml

# HTTP log receiver port (Railway uses PORT env)
EXPOSE 8080

CMD ["vector", "--config", "/etc/vector/vector.toml"]

FROM redis:7-alpine

COPY ops/redis-entrypoint.sh /usr/local/bin/aiph-redis-entrypoint
RUN chmod 0755 /usr/local/bin/aiph-redis-entrypoint

ENTRYPOINT ["/usr/local/bin/aiph-redis-entrypoint"]

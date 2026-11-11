FROM node:24.15.0-bookworm-slim AS build
WORKDIR /app/apps/store-ropa
COPY apps/store-ropa/package.json apps/store-ropa/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/store-ropa/ ./
COPY packages/ /app/packages/
COPY shared/ /app/shared/
COPY configurations/ /app/configurations/
ENV NEXT_TELEMETRY_DISABLED=1
# Non-secret placeholders only in the build stage; runtime credentials are injected.
RUN PRODUCT_CONFIG=/app/configurations/clothing.json LPS_ROOT=/app \
    SESSION_SECRET=build-placeholder-session-not-a-secret-333333333 \
    WEB_CATALOG_TOKEN=build-placeholder-not-a-secret-000000000 \
    WEB_ORDERS_TOKEN=build-placeholder-not-a-secret-111111111 \
    WEB_PAYMENTS_TOKEN=build-placeholder-not-a-secret-222222222 \
    WEB_RECOMMENDATIONS_TOKEN=build-placeholder-not-a-secret-444444444 npm run build

FROM node:24.15.0-bookworm-slim AS runtime
WORKDIR /app/apps/store-ropa
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 LPS_ROOT=/app
COPY --from=build /app/apps/store-ropa/package.json ./package.json
COPY --from=build /app/apps/store-ropa/node_modules ./node_modules
COPY --from=build /app/apps/store-ropa/.next ./.next
COPY --from=build /app/apps/store-ropa/public ./public
COPY --from=build /app/apps/store-ropa/next.config.ts ./next.config.ts
COPY --from=build /app/shared /app/shared
COPY --from=build /app/configurations /app/configurations
USER node
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]

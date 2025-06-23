FROM node:20-alpine AS builder

WORKDIR /app

COPY web/package*.json ./
RUN npm ci

COPY web .
RUN npm run build

# Production stage with Nginx
FROM nginx:1.25-alpine

# Copy built application
COPY --from=builder /app/out /usr/share/nginx/html

# Copy nginx configuration
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY web/package*.json ./
RUN npm ci

# Copy source code
COPY web .

# Build the application
RUN npm run build

# Production stage with Nginx
FROM nginx:1.25-alpine

# Copy built application
COPY --from=builder /app/out /usr/share/nginx/html

# Copy nginx configuration
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

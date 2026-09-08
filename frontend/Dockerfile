# ─── Stage 1: Development ───────────────────────────────────────────────────
FROM node:20-alpine AS development

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# ─── Stage 2: Production Builder ──────────────────────────────────────────
FROM development AS builder

RUN npm run build

# ─── Stage 3: Production Server (Nginx) ───────────────────────────────────
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

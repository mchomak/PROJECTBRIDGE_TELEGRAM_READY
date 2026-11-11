FROM node:24.22.2-alpine3.23

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --maxsockets=1 --fetch-retries=3 --fetch-timeout=120000

COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:22-alpine

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Vite 默认只监听容器内 localhost，这里显式绑定到 0.0.0.0，方便宿主机访问。
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

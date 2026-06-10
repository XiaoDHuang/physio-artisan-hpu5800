FROM registry.cn-shanghai.aliyuncs.com/sh-cloud/node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build


# ============ Runtime Stage ============
FROM registry.cn-shanghai.aliyuncs.com/sh-cloud/nginx:1.30-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx/app.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM node:16.16.0

WORKDIR /app

COPY package*.json .
RUN npm ci --dev

COPY src ./src

CMD ["./node_modules/.bin/parcel", "serve", "src/index.js", "--port", "1234"]
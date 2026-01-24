FROM node:20-alpine

WORKDIR /app
COPY server.js .

RUN npm install express node-fetch

EXPOSE 3000
CMD ["node", "server.js"]

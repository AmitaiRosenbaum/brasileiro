FROM node:18
WORKDIR /usr/local/app

COPY package.json package-lock.json ./

ENV VITE_API_URL='http://localhost:8000/'

RUN npm install

COPY . .

RUN npm run build

EXPOSE 8080

CMD ["npm", "run", "preview"]
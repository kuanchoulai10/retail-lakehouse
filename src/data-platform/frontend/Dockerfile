FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY src/design-system/package.json src/design-system/package.json
COPY src/data-platform/frontend/package.json src/data-platform/frontend/package.json
RUN npm ci --workspace src/data-platform/frontend --include-workspace-root=false
COPY src/design-system src/design-system
COPY src/data-platform/frontend src/data-platform/frontend
RUN npm --prefix src/data-platform/frontend run build

FROM nginx:1.29-alpine
COPY src/data-platform/frontend/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/src/data-platform/frontend/dist /usr/share/nginx/html/console
RUN chown -R nginx:nginx /usr/share/nginx/html
USER 101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
USER 101:101
EXPOSE 8443
ENTRYPOINT ["nginx", "-g", "daemon off;"]

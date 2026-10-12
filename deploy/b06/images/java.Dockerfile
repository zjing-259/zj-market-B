ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /app
COPY app.jar /app/app.jar
COPY HealthProbe.class /app/HealthProbe.class
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]

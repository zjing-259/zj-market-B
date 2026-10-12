# Full deployment uses scripts/build-b06-images.py and deploy/b06/compose.yml.
# This standalone B image also excludes verification and external private configuration.
FROM eclipse-temurin@sha256:f04fb34e053148344e83317976114ec3f37e4b830ec8bdab5a2fe3cecd7d010b
WORKDIR /app
COPY zj-market-app/target/zj-market-app-exec.jar /app/zj-market.jar
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=60s CMD curl --fail --silent http://127.0.0.1:8080/internal/health/live || exit 1
ENTRYPOINT ["java", "-jar", "/app/zj-market.jar"]

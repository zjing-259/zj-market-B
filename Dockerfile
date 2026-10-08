# Build with B's JDK 21 Maven entry first; shared contract remains a local build dependency.
FROM eclipse-temurin:21-jdk
WORKDIR /app
RUN java --version 2>&1 | grep -E '^(openjdk|java) 21([ .+-]|$)'
COPY zj-market-app/target/zj-market-app-exec.jar /app/zj-market.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/zj-market.jar"]

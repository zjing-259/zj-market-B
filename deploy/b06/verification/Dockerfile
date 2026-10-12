ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /tools
COPY libs/ /tools/libs/
COPY classes/ /tools/classes/
USER 10001:10001
ENTRYPOINT ["java", "-Xmx192m", "-Duser.home=/tmp", "-Dtls.enable=true", "-Dtls.test.mode.enable=false", "-Dtls.client.authServer=true", "-Dtls.config.file=/etc/b06/mq-tls.properties", "-cp", "/tools/classes:/tools/libs/*", "SecurityProbe"]

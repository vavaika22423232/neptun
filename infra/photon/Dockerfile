FROM eclipse-temurin:21-jre
WORKDIR /photon

# Install wget
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Download Photon 1.0.1 JAR
RUN wget https://github.com/komoot/photon/releases/download/1.0.1/photon-1.0.1.jar -O photon.jar

EXPOSE 2322

# Photon 1.x requires the serve subcommand (see komoot/photon docs/usage.md).
# Bind 0.0.0.0 so Docker -p 2322:2322 reaches the process (not only loopback).
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar photon.jar serve -listen-ip 0.0.0.0"]

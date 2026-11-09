# Book&Ride - Unit 05 - OpenSSH server + SFTP (DEVOP2 U11 sheets 19 and 23)
# Same commands as the sheets (apt install openssh-server), in a container.
FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd \
 && rm -f /etc/ssh/ssh_host_*            # host keys are NOT baked into the image
RUN useradd --create-home --shell /bin/bash student \
 && install -d -o student -m 700 /home/student/.ssh \
 && install -d -o student -m 755 /home/student/upload
COPY bookride.conf /etc/ssh/sshd_config.d/bookride.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
EXPOSE 22
HEALTHCHECK --interval=5s --timeout=3s --retries=10 CMD bash -c '</dev/tcp/127.0.0.1/22'
ENTRYPOINT ["/entrypoint.sh"]

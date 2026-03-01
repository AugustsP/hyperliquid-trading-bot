FROM python:3.12

# create and switch to ubuntu user
ENV PATH /home/ubuntu/.local/bin:/code/:$PATH

RUN useradd -rm -d /home/ubuntu -s /bin/bash -g root -G sudo -u 1001 ubuntu && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER ubuntu
WORKDIR /code
ENV PYTHONUNBUFFERED 1
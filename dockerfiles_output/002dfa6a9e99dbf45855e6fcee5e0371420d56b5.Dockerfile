# syntax=docker/dockerfile:1.3
# GOSINT DockerFile
#
# VERSION 1.0

FROM golang:1.8

MAINTAINER "Jason Soto <www.jasonsoto.com>"

#Install Dependencies

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/lib/apt --mount=type=cache,target=/var/cache/apt apt-get update && \
    apt-get -y install wget nginx mongodb php5-fpm nginx git

# Create SSL Certs for Nginx
RUN mkdir /etc/nginx/ssl \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt -subj "/C=US/ST=NY/L=NY/O=IT/OU=IT/CN=ssl.gosint"

#Add config file for nginx
ADD default.conf /etc/nginx/sites-available/default

RUN --mount=type=cache,target=/root/.cache/go-build go get github.com/tools/godep \ 
    && go install github.com/tools/godep

WORKDIR /go/src/

#Clone GOSINT Repository

RUN git clone https://github.com/ciscocsirt/GOSINT

WORKDIR /go/src/GOSINT/

COPY gosint.sh gosint.sh
RUN chmod 655 gosint.sh

RUN --mount=type=cache,target=/root/.cache/go-build go build -o gosint \
    && chmod +x gosint

RUN mkdir /var/www/gosint \
    && cp -r website/* /var/www/gosint/ \
    && chown -R www-data:www-data /var/www/gosint/

#start gosint

CMD ["./gosint.sh"]

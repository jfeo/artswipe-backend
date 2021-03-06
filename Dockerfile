FROM debian:buster
MAINTAINER jfeo "jensfeodor@gmail.dk"
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY app/requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY app/ /app/
EXPOSE 5000
ENTRYPOINT ["uwsgi", "--ini", "/app/uwsgi.ini"]

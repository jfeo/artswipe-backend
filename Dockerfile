FROM debian:buster
MAINTAINER jfeo "jensfeodor@gmail.dk"
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python3", "kultinder.py"]

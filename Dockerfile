FROM debian:buster
MAINTAINER jfeo "jensfeodor@gmail.dk"
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY assets.csv /app/assets.csv
COPY artswipe.py /app/artswipe.py
EXPOSE 5000
ENTRYPOINT ["python3", "artswipe.py"]

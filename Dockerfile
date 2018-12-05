FROM debian:buster
MAINTAINER jfeo "jensfeodor@gmail.dk"
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY requirements.txt /requirements.txt
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
RUN pip3 install -r requirements.txt
COPY uwsgi.ini /uwsgi.ini
COPY app/ /app/
COPY artswipe.py artswipe.py
RUN FLASK_APP="artswipe:app" flask db init && flask db migrate && flask db upgrade
EXPOSE 8000
ENTRYPOINT ["uwsgi", "--ini", "/uwsgi.ini"]

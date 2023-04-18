FROM python:3.11

ADD requirements.txt /tmp/
WORKDIR /tmp
RUN pip install -r requirements.txt
ADD worker.py /opt/app/
WORKDIR /opt/app/
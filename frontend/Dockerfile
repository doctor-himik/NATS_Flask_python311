FROM python:3.11

COPY requirements.txt /opt/app/requirements.txt
WORKDIR /opt/app
RUN pip install -r requirements.txt
ADD frontend.py .
RUN mkdir -p /opt/app/pages
COPY pages/main_page.html /opt/app/pages/main_page.html

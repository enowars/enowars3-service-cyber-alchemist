FROM python:alpine3.8

RUN pip install flask gunicorn Flask-Session hexdump

WORKDIR /app

CMD gunicorn -b [::]:80 app:app --access-logfile - --reload
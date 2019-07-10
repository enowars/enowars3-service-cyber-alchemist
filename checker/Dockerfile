FROM python
LABEL maintainer="ENOFLAG <mail@enoflag.de>"

# Install python3 and uswgi
#RUN apt-get update
#RUN apt-get install -y nginx git

# use python3
RUN pip3 install uwsgi

# copy our files in.
WORKDIR /checker
COPY ./requirements.txt /checker/requirements.txt
RUN pip3 install -r requirements.txt

COPY ./uwsgi.ini uwsgi.ini
COPY ./words.txt words.txt
COPY ./app.py app.py
COPY ./checker.py checker.py

#ENTRYPOINT ["/bin/bash"]
ENTRYPOINT [ "uwsgi", "--uid", "uwsgi", \
               "--socket", "[::]:3031", \
               "--protocol", "http", \
               "--ini", "/checker/uwsgi.ini" ]

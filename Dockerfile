FROM python:3.8.2-alpine3.11
VOLUME /cache
RUN apk --no-cache add git openssh
ADD . /etc/forksync
RUN pip install -r /etc/forksync/requirements.txt
CMD ["python", "/etc/forksync/forksync.py"]
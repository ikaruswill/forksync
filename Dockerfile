FROM python:3.10.5-alpine3.16
VOLUME /cache
RUN apk --no-cache add git openssh
ADD . /etc/forksync
RUN pip install -r /etc/forksync/requirements.txt
CMD ["python", "/etc/forksync/forksync.py"]
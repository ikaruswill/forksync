FROM alpine:3.9
RUN apk --no-cache add git openssh bash
WORKDIR /app
VOLUME /repos

ADD . /app
ENTRYPOINT [ "./sync-fork-tags.sh" ]
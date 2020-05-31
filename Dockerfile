FROM alpine:3.9
RUN apk --no-cache add git openssh bash
VOLUME /repos

ADD . /app
ENTRYPOINT [ "/app/sync-fork-tags.sh" ]
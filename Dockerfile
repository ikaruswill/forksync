FROM ikaruswill/git
RUN apk --no-cache add bash
WORKDIR /app
VOLUME /repos

ADD . /app
ENTRYPOINT [ "sync-fork-tags.sh" ]
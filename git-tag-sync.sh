#!/usr/bin/env bash

# Required:
# WORKDIR
# REPO
# UPSTREAM
# SSH_KEY
echo "Configuring SSH..."
KNOWN_HOSTS_FILE='./known_hosts'
SSH_PRIVATE_KEY_FILE='./id_rsa'

SSH_PATH=$HOME/.ssh/
mkdir -p $SSH_PATH
cp $KNOWN_HOSTS_FILE $SSH_PATH
cp $SSH_PRIVATE_KEY_FILE $SSH_PATH

REPO_URL='https://github.com/ikaruswill/gitea.git'
UPSTREAM='https://github.com/go-gitea/gitea.git'
REPO_PATH='/repo'

echo "Checking repo URL..."
REPO_HTTPS_URL=`echo $REPO_URL | sed -Ene's#.*(https://[^[:space:]]*).*#\1#p'`
if [ -z "$REPO_HTTPS_URL" ]; then
    echo "Repo URL is using SSH"
else
    echo "Repo URL is using HTTPS, converting to SSH..."
    USER=`echo $REPO_HTTPS_URL | sed -Ene's#https://github.com/([^/]*)/(.*).git#\1#p'`
    if [ -z "$USER" ]; then
        echo "-- ERROR:  Could not identify User."
        exit
    fi

    REPO=`echo $REPO_HTTPS_URL | sed -Ene's#https://github.com/([^/]*)/(.*).git#\2#p'`
    if [ -z "$REPO" ]; then
        echo "-- ERROR:  Could not identify Repo."
        exit
    fi

    NEW_URL="git@github.com:$USER/$REPO.git"
    echo "Changing repo url from "
    echo "  '$REPO_HTTPS_URL'"
    echo "      to "
    echo "  '$NEW_URL'"
    echo ""

    REPO_URL=$NEW_URL
fi

echo "Cloning repository..."
mkdir -p $REPO_PATH
git clone $REPO_URL $REPO_PATH
cd $REPO_PATH
git remote add upstream $UPSTREAM

echo "Fetching tags..."
TAGS=$(git fetch upstream --tags 2>&1 | sed -n 's/^.*\[new tag\].*->\s*\(.*\).*$/\1/p')

if [ -z "$TAGS" ]; then
    echo "Origin up-to-date with upstream"
else 
    echo "Origin behind upstream"
    for tag in $TAGS; do
        echo "Pushing $tag..."
        git push origin $tag
    done
fi

echo "Done"
#!/usr/bin/env bash

######################################################################################
##                                 sync-fork-tags                                   ##
######################################################################################
# A simple bash script to pull upstream tags of a fork and then push them to origin.
# - To be used in a cron job (e.g. K8s CronJob) to triggering CICD pipelines in forked
#   repositories that build on 'tag' events.
# - For people who build their own versions of forked repositories yet want to remain
#   as close as possible to upstream.

# Environment variables
# REPO_URL              : Forked repository URL
# UPSTREAM_URL          : Upstream repository URL
# SSH_PRIVATE_KEY_FILE  : Path to SSH private key with push access

set -e

# SSH variables
KNOWN_HOSTS_FILE=${KNOWN_HOSTS_FILE:-'./known_hosts'}
SSH_PRIVATE_KEY_FILE=${SSH_PRIVATE_KEY_FILE:-}
SSH_PATH="$HOME/.ssh"

# Repository variables
REPO_URL=${REPO_URL:-}
UPSTREAM_URL=${UPSTREAM_URL:-}
REPO_ROOT='/repos'

# Check environment variables
if [ -z "$REPO_URL" ]; then
    echo 'Missing REPO_URL'
    exit 1
elif [ -z "$UPSTREAM_URL" ]; then
    echo 'Missing UPSTREAM_URL'
    exit 1
elif [ -z $SSH_PRIVATE_KEY_FILE ]; then
    echo 'Missing SSH_PRIVATE_KEY_FILE'
    exit 1
elif ! [ -f "$SSH_PRIVATE_KEY_FILE" ]; then
    echo "SSH key not found at: $SSH_PRIVATE_KEY_FILE"
    exit 1
elif ! [ -f "$KNOWN_HOSTS_FILE" ]; then
    echo "known_hosts not found at: $KNOWN_HOSTS_FILE"
    echo "Using default known_hosts..."
    KNOWN_HOSTS_FILE='./known_hosts'
fi
[[ $REPO_URL == *.git ]] || REPO_URL+=.git
[[ $UPSTREAM_URL == *.git ]] || UPSTREAM_URL+=.git

configure_ssh () {
    mkdir -p $SSH_PATH
    cp $KNOWN_HOSTS_FILE $SSH_PATH/
    cp $SSH_PRIVATE_KEY_FILE $SSH_PATH/id_rsa
    chmod 600 $SSH_PATH/id_rsa
}

check_repo_url () {
    local REPO_HTTPS_URL=$(echo $REPO_URL | sed -Ene's#.*(https://[^[:space:]]*).*#\1#p')
    if [ -z "$REPO_HTTPS_URL" ]; then
        echo "Repo URL is using SSH"
    else
        echo "WARNING: Repo URL is using HTTPS, attemping conversion to SSH..."
        local USER=$(echo $REPO_HTTPS_URL | sed -Ene's#https://github.com/([^/]*)/(.*).git#\1#p')
        if [ -z "$USER" ]; then
            echo "-- ERROR:  Could not identify User."
            exit 1
        fi

        local REPO=$(echo $REPO_HTTPS_URL | sed -Ene's#https://github.com/([^/]*)/(.*).git#\2#p')
        if [ -z "$REPO" ]; then
            echo "-- ERROR:  Could not identify Repo."
            exit 1
        fi

        local NEW_URL="git@github.com:$USER/$REPO.git"
        echo "Changing repo url from "
        echo "  '$REPO_HTTPS_URL'"
        echo "      to "
        echo "  '$NEW_URL'"
        echo ""

        REPO_URL=$NEW_URL
    fi
}

pull_or_clone_repo () {
    if [ -d $REPO_PATH ]; then
        echo "Local repo exists"
        echo "Pulling repository..."
        git -C $REPO_PATH pull origin
    else 
        echo "Local repo not cloned yet"
        echo "Cloning repository..."
        git clone $REPO_URL $REPO_PATH
        echo "Adding upstream..."
        git -C $REPO_PATH remote add upstream $UPSTREAM_URL
    fi
}

push_tags () {
    if [ -z "$TAGS" ]; then
        echo "Origin up-to-date with upstream"
    else 
        echo "Origin behind upstream"
        for tag in $TAGS; do
            echo "Pushing $tag..."
            git -C $REPO_PATH push origin $tag
        done
    fi
}

echo "Configuring SSH..."
configure_ssh

echo "Checking repo URL..."
check_repo_url

echo "Pull or clone repository..."
REPO=$(echo $REPO_URL | sed -n 's/^.*\/\(.*\)\.git$/\1/p')
REPO_PATH=$REPO_ROOT/$REPO
pull_or_clone_repo

echo "Fetching tags..."
TAGS=$(git -C $REPO_PATH fetch upstream --tags 2>&1 | sed -n 's/^.*\[new tag\].*->\s*\(.*\).*$/\1/p')

push_tags

echo "Done"
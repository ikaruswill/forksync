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

REPO='https://github.com/ikaruswill/gitea.git'
UPSTREAM='https://github.com/go-gitea/gitea.git'
REPO_PATH='/repo'

echo "Cloning repository..."
mkdir -p $REPO_PATH
git clone $REPO $REPO_PATH
cd $REPO_PATH
git remote add upstream $UPSTREAM

echo "Fetching tags..."
TAGS=($(git fetch upstream --tags 2>&1 | sed -n 's/^.*\[new tag\].*->\s*\(.*\).*$/\1/p' | tr '\n' '\0'))

for tag in $TAGS; do
    echo "Pushing $tag..."
    git push origin $tag
done

echo "Done"
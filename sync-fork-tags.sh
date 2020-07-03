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
# SYNC_MASTER           : Set to 'true' to sync master with upstream by rebasing

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# SSH variables
KNOWN_HOSTS_FILE=${KNOWN_HOSTS_FILE:-"${DIR}/known_hosts"}
SSH_PRIVATE_KEY_FILE=${SSH_PRIVATE_KEY_FILE:-}
SSH_PATH="${HOME}/.ssh"

# Repository variables
REPO_URL=${REPO_URL:-}
UPSTREAM_URL=${UPSTREAM_URL:-}
SYNC_MASTER=${SYNC_MASTER:-'false'}
REPO_ROOT='/repos'

# Repository path handling
REPO=$(echo "${REPO_URL}" | sed -n 's/^.*\/\(.*\)\.git$/\1/p')
REPO_PATH="${REPO_ROOT}/${REPO}"
# Overrride git to use REPO_PATH
git() {
    /usr/bin/git -C ${REPO_PATH} "$@"
}

# Logging
LOG_ERROR=${LOG_ERROR:-'1'}
LOG_WARNING=${LOG_WARNING:-'1'}
LOG_INFO=${LOG_INFO:-'1'}

exec 3>&1
__log_error() {
    [[ "${LOG_ERROR}" == "1" ]] && echo -e "[ERROR]: $*" 1>&3
}

__log_warning() {
    [[ "${LOG_WARNING}" == "1" ]] && echo -e "[WARNING]: $*" 1>&3
}

__log_info() {
    [[ "${LOG_INFO}" == "1" ]] && echo -e "[INFO]: $*" 1>&3
}

# Check environment variables
if [ -z "${REPO_URL}" ]; then
    __log_error 'Missing REPO_URL'
    exit 1
elif [ -z "${UPSTREAM_URL}" ]; then
    __log_error 'Missing UPSTREAM_URL'
    exit 1
elif [ -z "${SSH_PRIVATE_KEY_FILE}" ]; then
    __log_error 'Missing SSH_PRIVATE_KEY_FILE'
    exit 1
elif ! [ -f "${SSH_PRIVATE_KEY_FILE}" ]; then
    __log_error "SSH key not found at: ${SSH_PRIVATE_KEY_FILE}"
    exit 1
elif ! [ -f "${KNOWN_HOSTS_FILE}" ]; then
    __log_warning "known_hosts not found at: ${KNOWN_HOSTS_FILE}"
    __log_warning "Using default known_hosts..."
    KNOWN_HOSTS_FILE='./known_hosts'
fi
[[ "${REPO_URL}" == *.git ]] || REPO_URL+=.git
[[ "${UPSTREAM_URL}" == *.git ]] || UPSTREAM_URL+=.git

configure_ssh() {
    mkdir -p ${SSH_PATH}
    cp ${KNOWN_HOSTS_FILE} ${SSH_PATH}/
    cp ${SSH_PRIVATE_KEY_FILE} ${SSH_PATH}/id_rsa
    chmod 600 ${SSH_PATH}/id_rsa
}

check_repo_url() {
    local -r repo_url="${1}"
    local -r repo_https_url=$(echo ${repo_url} | sed -En 's#.*(https://[^[:space:]]*).*#\1#p')
    if [ -z "${repo_https_url}" ]; then
        __log_info "Repo URL is using SSH"
        echo ${repo_url}
    else
        __log_warning "Repo URL is using HTTPS, attemping conversion to SSH..."
        local -r user=$(echo ${repo_https_url} | sed -En 's#https://github.com/([^/]*)/(.*).git#\1#p')
        if [ -z "${user}" ]; then
            __log_error "Could not identify User."
            exit 1
        fi

        local -r repo=$(echo ${repo_https_url} | sed -En 's#https://github.com/([^/]*)/(.*).git#\2#p')
        if [ -z "${repo}" ]; then
            __log_error "Could not identify Repo."
            exit 1
        fi

        local -r new_url="git@github.com:${user}/${repo}.git"
        __log_info "Changing Repo URL "
        __log_info "Old URL: '${repo_https_url}'"
        __log_info "New URL: '${new_url}'"
        echo ${new_url}
    fi
}

fetch_or_clone_repo() {
    if [ -d "${REPO_PATH}" ]; then
        __log_info "Local repo exists"
        __log_info "Fetching repository tags..."
        git fetch --tags --prune --prune-tags
    else 
        __log_info "Local repo not cloned yet"
        __log_info "Cloning repository..."
        mkdir -p "${REPO_PATH}"
        git clone "${REPO_URL}" "${REPO_PATH}"
        __log_info "Adding upstream..."
        git remote add upstream "${UPSTREAM_URL}"
    fi
}

fetch_and_push_tags() {
    local -r tags=$(git fetch upstream --tags 2>&1 | sed -n 's/^.*\[new tag\].*->\s*\(.*\).*$/\1/p')
    if [ -z "${tags}" ]; then
        __log_info "Origin up-to-date with upstream"
    else 
        __log_info "Origin behind upstream"
        for tag in ${tags}; do
            __log_info "Pushing ${tag}..."
            git push origin ${tag}
        done
    fi
}

sync_master() {
    git checkout master
    git pull origin
    git fetch upstream master
    git diff upstream/master master --exit-code > /dev/null
    local isDiff=$?
    if [[ isDiff == 0 ]]; then
        __log_info "origin/master up to date with upstream/master"
    else
        __log_info "origin/master behind upstream/master"
        __log_info "Rebasing origin/master onto upstream/master..."
        git rebase upstream/master
    fi
}

__log_info "Configuring SSH..."
configure_ssh

__log_info "Checking repo URL..."
REPO_URL="$(check_repo_url ${REPO_URL})"

__log_info "Checking local repo..."
fetch_or_clone_repo

__log_info "Fetching and pushing tags..."
fetch_and_push_tags

if [[ "${SYNC_MASTER}" == "true" ]]; then
    __log_info "Syncing master..."
    sync_master
fi

__log_info "Done"

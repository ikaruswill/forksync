# sync-fork-tags

A simple bash script to pull upstream tags of a fork and then push them to origin.
- To be used in a cron job (e.g. K8s CronJob) to triggering CICD pipelines in forked
  repositories that build on 'tag' events.
- For people who build their own versions of forked repositories yet want to remain
  as close as possible to upstream.

## Usage
```bash
docker run --rm \
-e "REPO_URL=git@github.com:username/repo.git" \
-e "UPSTREAM_URL=git@github.com:upstream_user/repo.git" \
-e "SSH_PRIVATE_KEY_FILE=/id_rsa" \
-v path/to/ssh/privatekey:/id_rsa \
ikaruswill/sync-fork-tags
```

## Environment variables
```
REPO_URL              : Forked repository URL
UPSTREAM_URL          : Upstream repository URL
SSH_PRIVATE_KEY_FILE  : Path to SSH private key with push access
```

## Volumes
```
/repos                : Repository cache (to avoid clone on every run)
```
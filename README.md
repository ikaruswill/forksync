# Forksync

A python script to push new tags in the upstream repository to your fork.
- Can be used in a cron job (e.g. K8s CronJob) to trigger CICD pipelines in forked
  repositories that build on `tag` events.
- For people who build their own versions of forked repositories yet want to remain
  as close as possible to upstream.

## Features
- Multiple repositories can be kept synchronized with the upstream defined in a single yaml configuration file
- Repositories can be cached on disk to speed up executions by minimizing cloning and fetching

## Usage
```bash
docker run --rm \
-v path/to/config.yaml:/etc/forksync/config.yaml \
-v cache:/cache \
ikaruswill/forksync
```

## Configuration
| Variable                | Description                              | Default      |
|-------------------------|------------------------------------------|--------------|
| ssh_key                 | Path to SSH private key with push access | **Required** |
| cache_dir               | Directory to cache repositories in       | /cache       |
| repositories            | List of repository configurations        | **Required** |
| repositories[].origin   | SSH URL of your fork                     | **Required** |
| repositories[].upstream | SSH URL of the upstream repository       | **Required** |
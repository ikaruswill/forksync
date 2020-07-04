import argparse
import logging
import os
import shutil
import urllib

import confuse
import git

APP_NAME = 'forksync'
CONFIG_TEMPLATE = {
    'ssh_key': confuse.Filename(),
    'cache_dir': confuse.Filename(),
    'repositories': confuse.Sequence(
        {
            'origin': confuse.String(),
            'upstream': confuse.String()
        }
    )
}


def setup_ssh(repo, ssh_key):
    repo.git.update_environment(GIT_SSH=f'ssh -i {ssh_key}')


def fix_https_url(url):
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    return os.path.join(f'ssh://git@{netloc}', path)


def fix_ssh_url(url):
    host, path = url.split(':')
    return os.path.join('ssh://', host, path)


def validate_url(url):
    if url.startswith('https://'):
        return fix_https_url(url)
    if not url.startswith('ssh://'):
        return fix_ssh_url(url)
    return url


def parse_repo(url):
    path = urllib.parse.urlsplit(url).path.strip('/')
    org, filename = os.path.split(path)
    repo, ext = os.path.splitext(filename)
    return org, repo


def run_repo(ssh_key, cache_dir, repo_config):
    org, repo = parse_repo(repo_config['origin'])
    repo_id = os.path.join(org, repo)
    repo_path = os.path.join(cache_dir, repo)

    logger.info(f'Processing repository: {repo_id}')

    # Check cache
    try:
        repo = git.Repo(repo_path)
        logger.info('Repository cache hit')
    except git.exc.NoSuchPathError:
        logger.info('Repository cache miss, cloning...')
        repo = git.Repo.clone_from(repo_config['origin'], repo_path)
    except git.exc.InvalidGitRepositoryError:
        logger.warning('Cached repository invalid, reinitializing...')
        shutil.rmtree(repo_path)
        repo = git.Repo.clone_from(repo_config['origin'], repo_path)

    # Check origin
    try:
        origin = repo.remote('origin')
    except ValueError:
        logger.warning('Origin missing from cached repository, reinitializing...')
        shutil.rmtree(repo_path)
        repo = git.Repo.clone_from(repo_config['origin'], repo_path)
        origin = repo.remote('origin')

    # Check upstream
    try:
        upstream = repo.remote('upstream')
    except ValueError:
        logger.warning('Upstream missing, adding upstream...')
        upstream = repo.create_remote('upstream', repo_config['upstream'])

    # Sync origin
    logger.info('Fetching latest state from origin')
    origin_fetch = origin.fetch(tags=True, prune=True, prune_tags=True)
    current_tags = repo.tags

    # Sync upstream
    upstream_fetch = upstream.fetch(tags=True)
    new_tags = repo.tags

    # Check upstream against cache
    missing_tags = list(set(new_tags) - set(current_tags))
    if len(missing_tags):
        logger.info('Origin is behind upstream')
        tag_push_order = sorted(
            missing_tags, key=lambda t: t.commit.committed_datetime)

        # Push each tag individually
        # Github has webhook limit of 3 tags per push
        origin_push = []
        for tag_ref in tag_push_order:
            logger.info(f'Pushing {tag_ref.name}...')
            origin_push.append(
                origin.push(f'{tag_ref.path}:{tag_ref.path}')[0])
    else:
        logger.info('Origin is up-to-date with upstream')

    logger.info('Done')


def run(ssh_key, cache_dir, repositories):
    for repo_config in repositories:
        repo_config['origin'] = validate_url(repo_config['origin'])
        repo_config['upstream'] = validate_url(repo_config['upstream'])
        run_repo(ssh_key, cache_dir, repo_config)
    logger.info('forksync complete')


def main():
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description='Keep a fork synchronized with its upstream')
    parser.add_argument(
        '--ssh-key',
        help='Path to SSH private key with push access')
    parser.add_argument(
        '--cache-dir',
        help='Directory to cache repositories in')

    args = parser.parse_args()
    config = confuse.LazyConfig(APP_NAME, __name__)
    config.set_args(args)
    valid = config.get(CONFIG_TEMPLATE)
    run(**valid)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(APP_NAME)
    main()
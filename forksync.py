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
    'cache_dir': confuse.Filename(default='/cache'),
    'log_level': confuse.String(default='INFO'),
    'repositories': confuse.Sequence(
        {
            'origin': confuse.String(),
            'upstream': confuse.String()
        }
    )
}


def fix_https_url(url):
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    return os.path.join(f'ssh://git@{netloc}', path)


def fix_ssh_url(url):
    host, path = url.split(':')
    return os.path.join('ssh://', host, path)


def validate_url(url):
    if url.startswith('https://'):
        logger.debug('Converting remote URL from HTTPS to SSH')
        logger.debug(f'URL: {url}')
        new_url = fix_https_url(url)
        logger.debug(f'New URL: {new_url}')
        return new_url
    if not url.startswith('ssh://'):
        logger.debug('Converting remote URL from HTTPS to SSH')
        logger.debug(f'URL: {url}')
        new_url = fix_ssh_url(url)
        logger.debug(f'New URL: {new_url}')
        return new_url
    return url


def parse_repo(url):
    path = urllib.parse.urlsplit(url).path.strip('/')
    org, filename = os.path.split(path)
    repo, ext = os.path.splitext(filename)
    return org, repo


def handle_fetchinfos(fetchinfos):
    for fetchinfo in fetchinfos:
        if fetchinfo.flags & git.FetchInfo.ERROR:
            logger.debug('ERROR')
        if fetchinfo.flags & git.FetchInfo.FAST_FORWARD:
            logger.debug('FAST_FORWARD')
        if fetchinfo.flags & git.FetchInfo.FORCED_UPDATE:
            logger.debug('FORCED_UPDATE')
        if fetchinfo.flags & git.FetchInfo.HEAD_UPTODATE:
            logger.debug('HEAD_UPTODATE')
            logger.info(f'UP TO DATE: {fetchinfo.name}')
        if fetchinfo.flags & git.FetchInfo.NEW_HEAD:
            logger.debug('NEW_HEAD')
        if fetchinfo.flags & git.FetchInfo.NEW_TAG:
            logger.debug('NEW_TAG')
            logger.info(f'NEW TAG: {fetchinfo.name}')
        if fetchinfo.flags & git.FetchInfo.REJECTED:
            logger.debug('REJECTED')
        if fetchinfo.flags & git.FetchInfo.TAG_UPDATE:
            logger.debug('TAG_UPDATE')
            logger.info(f'UPDATED TAG: {fetchinfo.name}')


def handle_pushinfos(pushinfos):
    for pushinfo in pushinfos:
        if pushinfo.flags & git.PushInfo.DELETED:
            logger.debug('DELETED')
        if pushinfo.flags & git.PushInfo.ERROR:
            logger.debug('ERROR')
        if pushinfo.flags & git.PushInfo.FAST_FORWARD:
            logger.debug('FAST_FORWARD')
        if pushinfo.flags & git.PushInfo.FORCED_UPDATE:
            logger.debug('FORCED_UPDATE')
        if pushinfo.flags & git.PushInfo.NEW_HEAD:
            logger.debug('NEW_HEAD')
        if pushinfo.flags & git.PushInfo.NEW_TAG:
            logger.debug('NEW_TAG')
            logger.info(f'NEW TAG: {pushinfo.remote_ref.name}')
        if pushinfo.flags & git.PushInfo.NO_MATCH:
            logger.debug('NO_MATCH')
        if pushinfo.flags & git.PushInfo.REJECTED:
            logger.debug('REJECTED')
        if pushinfo.flags & git.PushInfo.REMOTE_FAILURE:
            logger.debug('REMOTE_FAILURE')
        if pushinfo.flags & git.PushInfo.REMOTE_REJECTED:
            logger.debug('REMOTE_REJECTED')
        if pushinfo.flags & git.PushInfo.UP_TO_DATE:
            logger.debug('UP_TO_DATE')
            logger.info(f'UP TO DATE: {pushinfo.remote_ref.name}')


def run_repo(cache_dir, repo_config):
    org, repo = parse_repo(repo_config['origin'])
    repo_id = os.path.join(org, repo)
    repo_path = os.path.join(cache_dir, repo)

    logger.info(f'Processing repository: {repo_id}')

    # Check cache
    try:
        repo = git.Repo(repo_path)
        logger.info('Cache hit')
    except git.exc.NoSuchPathError:
        logger.info('Cache miss, cloning...')
        repo = git.Repo.clone_from(repo_config['origin'], repo_path)
    except git.exc.InvalidGitRepositoryError:
        logger.warning('Cache invalid, reinitializing repo...')
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
    handle_fetchinfos(origin_fetch)
    current_tags = repo.tags

    # Sync upstream
    upstream_fetch = upstream.fetch(tags=True)
    new_tags = repo.tags
    handle_fetchinfos(upstream_fetch)

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

    handle_pushinfos(origin_push)
    logger.info('Done')


def run(ssh_key, cache_dir, log_level, repositories):
    os.environ['GIT_SSH_COMMAND'] = f'/usr/bin/ssh -o StrictHostKeyChecking=no -i {ssh_key}'
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    for repo_config in repositories:
        repo_config['origin'] = validate_url(repo_config['origin'])
        repo_config['upstream'] = validate_url(repo_config['upstream'])
        run_repo(cache_dir, repo_config)
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
        help='Directory to cache repositories in',
        default='/cache')
    parser.add_argument(
        '--log-level',
        help='Desired log level',
        default='INFO')

    args = parser.parse_args()
    config = confuse.LazyConfig(APP_NAME, __name__)
    config.set_args(args)
    valid = config.get(CONFIG_TEMPLATE)
    run(**valid)


if __name__ == "__main__":
    logger = logging.getLogger(APP_NAME)
    main()

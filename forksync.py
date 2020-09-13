import argparse
import logging
import os
import shutil
import urllib.parse

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
            'upstream': confuse.String(),
            'branches': confuse.StrSeq()
        }
    )
}
logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(APP_NAME)


def fix_https_url(url):
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    scheme = 'ssh'
    netloc = 'git@' + netloc

    if not path:
        raise ValueError(f'Invalid git remote URL: No path present in URL \'{url}\'')
    if len(path.strip('/').split('/')) < 2:
        raise ValueError(f'Invalid git remote URL: 2 path elements expected, got {path.strip("/").split("/")} - \'{url}\'')
    return urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))


def fix_ssh_url(url):
    scheme = 'ssh'
    try:
        netloc, path = url.split(':')
    except ValueError:
        raise ValueError(f'Invalid git remote URL: No path present in URL \'{url}\'')
    if len(path.strip('/').split('/')) < 2:
        raise ValueError(f'Invalid git remote URL: 2 path elements expected, got {path.strip("/").split("/")} \'{url}\'')
    return urllib.parse.urlunsplit((scheme, netloc, path, '', ''))


def validate_url(url):
    if url.endswith('/'):
        logger.warning(f'URL has trailing slash \'{url}\'')
        logger.info('Stripping trailing slash...')
        url = url.rstrip('/')
    if not url.endswith('.git'):
        logger.warning(f'URL does not end with .git, \'{url}\'')
        logger.info('Adding .git suffix...')
        url += '.git'
    if url.startswith('https://') or url.startswith('http://'):
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
            message = 'ERROR'
        elif fetchinfo.flags & git.FetchInfo.FAST_FORWARD:
            message = 'FAST FORWARD'
        elif fetchinfo.flags & git.FetchInfo.FORCED_UPDATE:
            message = 'FORCED UPDATE'
        elif fetchinfo.flags & git.FetchInfo.HEAD_UPTODATE:
            message = 'UP TO DATE'
        elif fetchinfo.flags & git.FetchInfo.NEW_HEAD:
            message = 'NEW_HEAD'
        elif fetchinfo.flags & git.FetchInfo.NEW_TAG:
            message = 'NEW TAG'
        elif fetchinfo.flags & git.FetchInfo.REJECTED:
            message = 'REJECTED'
        elif fetchinfo.flags & git.FetchInfo.TAG_UPDATE:
            message = 'TAG UPDATE'

        logger.info(f'{message:<15}: \t{fetchinfo.name}')


def handle_pushinfos(pushinfos):
    for pushinfo in pushinfos:
        if pushinfo.flags & git.PushInfo.DELETED:
            message = 'DELETED'
        elif pushinfo.flags & git.PushInfo.ERROR:
            message = 'ERROR'
        elif pushinfo.flags & git.PushInfo.FAST_FORWARD:
            message = 'FAST FORWARD'
        elif pushinfo.flags & git.PushInfo.FORCED_UPDATE:
            message = 'FORCED UPDATE'
        elif pushinfo.flags & git.PushInfo.NEW_HEAD:
            message = 'NEW HEAD'
        elif pushinfo.flags & git.PushInfo.NEW_TAG:
            message = 'NEW TAG'
        elif pushinfo.flags & git.PushInfo.NO_MATCH:
            message = 'NO MATCH'
        elif pushinfo.flags & git.PushInfo.REJECTED:
            message = 'REJECTED'
        elif pushinfo.flags & git.PushInfo.REMOTE_FAILURE:
            message = 'REMOTE FAILURE'
        elif pushinfo.flags & git.PushInfo.REMOTE_REJECTED:
            message = 'REMOTE REJECTED'
        elif pushinfo.flags & git.PushInfo.UP_TO_DATE:
            message = 'UP TO DATE'

        logger.info(f'{message:<15}: \t{pushinfo.remote_ref.name}')


def get_or_create_repo(repo_path, url):
    try:
        repo = git.Repo(repo_path)
        logger.info('Cache hit')
    except git.exc.NoSuchPathError:
        logger.info('Cache miss, cloning...')
        repo = git.Repo.clone_from(url, repo_path)
    except git.exc.InvalidGitRepositoryError:
        logger.warning('Cache invalid, reinitializing...')
        shutil.rmtree(repo_path)
        repo = git.Repo.clone_from(url, repo_path)
    return repo


def get_or_create_remote(repo, name, url):
    try:
        remote = repo.remote(name)
    except ValueError:
        logger.warning(f'Remote \'{name}\' missing, creating...')
        remote = repo.create_remote(name, url)
    return remote


def run_repo(cache_dir, repo_config):
    org, repo = parse_repo(repo_config['origin'])
    repo_path = os.path.join(cache_dir, repo)

    logger.info(f'Processing repository: {os.path.join(org, repo)}')

    # Init cache
    repo = get_or_create_repo(repo_path, repo_config['origin'])

    # Init origin
    origin = get_or_create_remote(repo, 'origin', repo_config['origin'])

    # Init upstream
    upstream = get_or_create_remote(repo, 'upstream', repo_config['upstream'])

    # Sync origin
    logger.info('Fetching latest state from origin')
    origin_fetch = origin.fetch(tags=True, prune=True, prune_tags=True, force=True)
    handle_fetchinfos(origin_fetch)
    current_tags = repo.tags

    # Sync upstream
    logger.info('Fetching latest state from upstream')
    upstream_fetch = upstream.fetch(tags=True, force=True)
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
                origin.push(f'{tag_ref.path}:{tag_ref.path}', force=True)[0])
        handle_pushinfos(origin_push)
    else:
        logger.info('Origin is up-to-date with upstream')

    logger.info('Done')


def run(ssh_key, cache_dir, log_level, repositories):
    os.environ['GIT_SSH_COMMAND'] = f'/usr/bin/ssh -o StrictHostKeyChecking=no -i {ssh_key}'
    logging.getLogger().setLevel(getattr(logging, log_level))

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
    main()

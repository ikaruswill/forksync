import logging
import os
import shutil

import git
import pytest

from forksync import (fix_https_url, fix_ssh_url, get_or_create_remote,
                      get_or_create_repo, parse_repo)


def test_fix_https_url_github():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url_http = 'https://github.com/ikaruswill/forksync.git'
    url_https = 'https://github.com/ikaruswill/forksync.git'
    url_https_nogitsuffix = 'https://github.com/ikaruswill/forksync'
    url_https_nopath = 'https://github.com'
    url_https_one_element_path = 'https://github.com/ikaruswill'

    assert fix_https_url(url_http) == target
    assert fix_https_url(url_https) == target
    assert fix_https_url(url_https_nogitsuffix) == target
    pytest.raises(ValueError, fix_https_url, url_https_nopath)
    pytest.raises(ValueError, fix_https_url, url_https_one_element_path)


def test_fix_ssh_url_github():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url_ssh = 'git@github.com:ikaruswill/forksync.git'
    url_ssh_nogitsuffix = 'git@github.com:ikaruswill/forksync'
    url_ssh_nopath = 'git@github.com:'
    url_ssh_nopath_nocolon = 'git@github.com'
    url_ssh_one_element_path = 'git@github.com:ikaruswill'

    assert fix_ssh_url(url_ssh) == target
    assert fix_ssh_url(url_ssh_nogitsuffix) == target
    pytest.raises(ValueError, fix_ssh_url, url_ssh_nopath)
    pytest.raises(ValueError, fix_ssh_url, url_ssh_nopath_nocolon)
    pytest.raises(ValueError, fix_ssh_url, url_ssh_one_element_path)


def test_parse_repo():
    target = ('ikaruswill', 'forksync')
    url = 'ssh://git@github.com/ikaruswill/forksync.git'
    assert parse_repo(url) == target


def test_get_or_create_repo_existing(tmpdir, caplog):
    remote_url = tmpdir.join('remote')
    remote_repo = git.Repo.init(tmpdir.join('remote'))
    cache_path = tmpdir.join('cache')
    repo_path = cache_path.join('repo')
    target = git.Repo.init(repo_path)
    with caplog.at_level(logging.INFO):
        assert get_or_create_repo(repo_path, remote_url) == target
        assert 'hit' in caplog.text


def test_get_or_create_repo_missing(tmpdir, caplog):
    remote_url = tmpdir.join('remote')
    remote_repo = git.Repo.init(tmpdir.join('remote'))
    cache_path = tmpdir.join('cache')
    repo_path = cache_path.join('repo')
    target = git.Repo.init(repo_path)
    shutil.rmtree(repo_path)

    with caplog.at_level(logging.INFO):
        assert get_or_create_repo(repo_path, remote_url) == target
        assert 'miss' in caplog.text


def test_get_or_create_repo_invalid(tmpdir, caplog):
    remote_url = tmpdir.join('remote')
    remote_repo = git.Repo.init(tmpdir.join('remote'))
    cache_path = tmpdir.join('cache')
    repo_path = cache_path.join('repo')
    target = git.Repo.init(repo_path)
    shutil.rmtree(repo_path)
    os.mkdir(repo_path)

    with caplog.at_level(logging.INFO):
        assert get_or_create_repo(repo_path, remote_url) == target
        assert 'invalid' in caplog.text


def test_get_or_create_remote_existing(tmpdir, caplog):
    remote_url = tmpdir.join('remote')
    remote_repo = git.Repo.init(tmpdir.join('remote'))
    cache_path = tmpdir.join('cache')
    repo_path = cache_path.join('repo')
    repo = git.Repo.clone_from(remote_url, repo_path)
    target = repo.remote('origin')

    assert get_or_create_remote(repo, 'origin', remote_url) == target

def test_get_or_create_remote_missing(tmpdir, caplog):
    remote_url = tmpdir.join('remote')
    repo_path = tmpdir.join('repo')
    target = git.Repo.init(repo_path).create_remote('upstream', remote_url)
    shutil.rmtree(repo_path)
    repo = git.Repo.init(repo_path)

    with caplog.at_level(logging.INFO):
        assert get_or_create_remote(repo, 'upstream', remote_url) == target

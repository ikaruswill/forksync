import logging
import os
import shutil

import git
import pytest

from forksync import (fix_https_url, fix_ssh_url, get_or_create_remote,
                      get_or_create_repo, parse_repo, validate_url)


def test_fix_https_url_github_http():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'http://github.com/ikaruswill/forksync.git'
    assert fix_https_url(url) == target


def test_fix_https_url_github_https():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'https://github.com/ikaruswill/forksync.git'
    assert fix_https_url(url) == target


def test_fix_https_url_github_no_path():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'https://github.com.git'
    pytest.raises(ValueError, fix_https_url, url)


def test_fix_https_url_github_one_element_path():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'https://github.com/ikaruswill.git'
    pytest.raises(ValueError, fix_https_url, url)


def test_fix_ssh_url_github_ssh():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'git@github.com:ikaruswill/forksync.git'
    assert fix_ssh_url(url) == target


def test_fix_ssh_url_github_no_path():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'git@github.com'
    url_with_colon = url + ':'
    pytest.raises(ValueError, fix_ssh_url, url)
    pytest.raises(ValueError, fix_ssh_url, url_with_colon)


def test_fix_ssh_url_github_one_path_element():
    target = 'ssh://git@github.com/ikaruswill/forksync.git'
    url = 'git@github.com:ikaruswill'
    pytest.raises(ValueError, fix_ssh_url, url)


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

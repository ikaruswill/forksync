import pytest
from forksync import fix_https_url, fix_ssh_url, parse_repo


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


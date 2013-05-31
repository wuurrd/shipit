# -*- coding: utf-8 -*-

"""
shipit.git
~~~~~~~~~~

Operations on git repositories.
"""

import os
import tempfile
import subprocess


def get_remotes():
    """
    Get a list of the git remote URLs for this repository.

    Return a dictionary of remote names mapped to URL strings if remotes were
    found.

    Otherwise return ``None``.
    """
    tmp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

    retcode = subprocess.call(['git', 'remote', '-v'], stdout=tmp_file.file)
    if retcode != 0:
        return

    # Store the output of the command and delete temporary file
    tmp_file.file.seek(0)
    raw_remotes = tmp_file.read()
    os.remove(tmp_file.name)

    # Get the GitHub remote strings
    nonempty_remotes = (r for r in raw_remotes.split('\n') if 'github' in r.lower())

    return {remote_name(r): remote_url(r)  for r in nonempty_remotes}


def remote_name(remotestring):
    return remotestring.split(' ')[0].split('\t')[0]


def remote_url(remotestring):
    return remotestring.split(' ')[0].split('\t')[1]


def extract_user_and_repo_from_remote(remote_url):
    # TODO: name slices
    if remote_url.startswith('git://'):
        # Git remote
        user_repo = remote_url.split('/')[3:]
        user, repo = user_repo[0], user_repo[1][:-4]
    elif remote_url.startswith('http'):
        # HTTP[S] remote
        user_repo = remote_url.split('/')[3:]
        user, repo = user_repo[0], user_repo[1][:-4]
    else:
        # SSH remote
        user_repo = remote_url.split(':')[1][:-4]
        user, repo = tuple(user_repo.split('/'))

    return user, repo

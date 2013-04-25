from argparse import ArgumentParser
import sys

from .ui import UI
from .core import Shipit
from .auth import login
from .git import get_remotes, extract_user_and_repo_from_remote


ERR_NOT_IN_REPO = 1
ERR_UNABLE_TO_FIND_REMOTE = 2
ERR_ORIGIN_REMOTE_NOT_FOUND = 3
ERR_NO_ISSUETRACKER = 4

VERSION = "alpha"


def read_arguments():
    """Read arguments from the command line and return a dictionary."""

    parser_title = "shipit"
    parser = ArgumentParser(parser_title)

    # Repo
    parser.add_argument("user/repository",
                        nargs='?',
                        default="",
                        help="The repository to show")

    # version
    version = "shipit %s" % VERSION
    parser.add_argument("-v",
                        "--version",
                        action="version",
                        version=version,
                        help="Show the current version of shipit")

    args = parser.parse_args()

    # Coerce `args` to a dictionary
    return vars(args)


def main():
    args = read_arguments()

    api = login()

    user = api.user()

    # Get the user and repository that we are we going to manage
    user_repo_arg = args['user/repository'].strip()

    if not user_repo_arg:
        remotes = get_remotes()

        if remotes is None:
            # We aren't in a git repo
            exit(ERR_NOT_IN_REPO)
        elif not remotes:
            # No github remotes were found
            exit(ERR_UNABLE_TO_FIND_REMOTE)

        # Try an `upstream` remote first, and fall back to `origin` if it
        # wasn't found.
        remote = remotes.get("upstream") or remotes.get("origin")

        if remote is None:
            exit(ERR_ORIGIN_REMOTE_NOT_FOUND)

        USER, REPO = extract_user_and_repo_from_remote(remote)
    elif '/' in user_repo_arg:
        # Assume that we got a <username>/<repository>
        USER, REPO = user_repo_arg.split('/')
    else:
        # If a `/` isn't included, assume that it's the name of the repository
        # and the logged in user owns it
        USER, REPO = str(user), user_repo_arg

    # fetch repo
    repo = api.repository(USER, REPO)
    while not repo.has_issues:
        if repo.fork:
            repo = repo.parent
        else:
            print('No issue tracker found.')
            sys.exit(ERR_NO_ISSUETRACKER)

    print('Loading: {}'.format(repo.full_name))

    # create view
    ui = UI(repo)

    # create controller
    shipit = Shipit(ui, repo, user)

    shipit.start()

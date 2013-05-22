# -*- coding: utf-8 -*-

"""
shipit.core
~~~~~~~~~~~

Glues everything together.
"""

import re
import os
import subprocess
import tempfile
import concurrent.futures
import webbrowser
from functools import partial

from urwid import MainLoop, ExitMainLoop

from .config import (
    PALETTE,

    KEY_OPEN_ISSUE, KEY_CLOSE_ISSUE, KEY_BACK, KEY_DETAIL, KEY_EDIT,
    KEY_REOPEN_ISSUE, KEY_COMMENT, KEY_DIFF, KEY_BROWSER, KEY_QUIT,
)
from .ui import time_since
from .events import on
from .func import lines, unlines, both
from .models import (
    is_issue, is_pull_request, is_comment, is_open, is_closed,

    IssuesAndPullRequests,
)

NEW_ISSUE = """
<!---
The first line will be used as the issue title. The rest will be the body of
the issue.
-->
"""

# '*?' is for a non-greedy matching strategy
# re.DOTALL makes newlines part of the characters that `.` matches
COMMENT_RE = re.compile('<!--.*?-->', re.DOTALL)

def strip_comments(text):
    return COMMENT_RE.sub('', text.strip())

def indent(text, indentation='    '):
    return indentation.join(['', text])

def format_issue_thread(issue):
    issue_thread = [format_issue_body(issue)]
    issue_thread.extend(format_comment(comment) for comment in issue.iter_comments())

    # Make the whole thread a comment
    issue_thread.insert(0, '<!---\n')
    issue_thread.append('-->')

    return issue_thread

def format_issue_body(issue):
    return '\n\n'.join([issue.title, issue.body_text, ''])

def format_comment(comment):
    author = str(comment.user)
    time = time_since(comment.created_at)

    body = lines(indent(line) for line in unlines(comment.body_text))

    return "{author} commented {time}\n\n{body}\n".format(author=author,
                                                          time=time,
                                                          body=body,)

def discard_args(func):
    def wrapper(*args, **kwargs):
        return func()
    return wrapper


class Shipit():
    ISSUE_LIST = 0
    ISSUE_DETAIL = 1
    PR_DETAIL = 2
    PR_DIFF = 3

    def __init__(self, ui, repo, user):
        self.ui = ui
        self.repo = repo
        self.user = user

        self.issues_and_prs = IssuesAndPullRequests(self.repo)
        self.issues_and_prs.set_modified_callback(self.on_modify_issues_and_prs)
        self.issues_and_prs.show_open_issues()

        # Event handlers
        on("show_all", self.issues_and_prs.show_all)

        created_by_you = partial(self.issues_and_prs.show_created_by, self.user)
        on("show_created_by_you", created_by_you)

        assigned_to_you = partial(self.issues_and_prs.show_assigned_to, self.user)
        on("show_assigned_to_you", assigned_to_you)

        mentioning_you = partial(self.issues_and_prs.show_mentioning, self.user)
        on("show_mentioning_you", mentioning_you)

        on("show_open_issues", self.issues_and_prs.show_open_issues)
        on("show_closed_issues", self.issues_and_prs.show_closed_issues)
        on("show_pull_requests", self.issues_and_prs.show_pull_requests)

        on("filter_by_labels", self.issues_and_prs.filter_by_labels)
        on("clear_label_filters", self.issues_and_prs.clear_label_filters)

    def start(self):
        self.loop = MainLoop(self.ui,
                             PALETTE,
                             handle_mouse=True,
                             unhandled_input=self.handle_keypress)
        self.loop.set_alarm_at(0, discard_args(self.issue_list))
        self.loop.run()

    def on_modify_issues_and_prs(self):
        self.ui.issues_and_pulls(self.issues_and_prs)

    def issue_list(self):
        self.mode = self.ISSUE_LIST
        self.ui.issues_and_pulls(self.issues_and_prs)
        self.loop.draw_screen()

    def issue_detail(self, issue):
        self.mode = self.ISSUE_DETAIL
        self.ui.issue(issue)
        self.loop.draw_screen()

    def pull_request_detail(self, pr):
        self.mode = self.PR_DETAIL
        self.ui.pull_request(pr)
        self.loop.draw_screen()

    def diff(self, pr):
        self.mode = self.PR_DIFF
        self.ui.diff(pr)
        self.loop.draw_screen()

    def handle_keypress(self, key):
        if key == KEY_OPEN_ISSUE:
            if self.mode is self.ISSUE_LIST:
                issue_text = self.spawn_editor(NEW_ISSUE)

                if issue_text is None:
                    # TODO: cancelled by the user
                    return

                contents = unlines(issue_text)
                title, *body = contents

                if not title:
                    # TODO: incorrect input, at least a title is needed
                    return
                body = lines(body)

                issue = self.repo.create_issue(title=title, body=body)

                if issue:
                    self.issue_detail(issue)
                else:
                    self.issue_list()
        elif key == KEY_CLOSE_ISSUE:
            issue = self.ui.get_issue()

            if not issue:
                return

            self.issues_and_prs.close(issue)

            if self.mode is self.ISSUE_DETAIL:
                self.issue_detail(issue)
        elif key == KEY_REOPEN_ISSUE:
            issue = self.ui.get_issue()

            if issue and is_closed(issue):
                self.issues_and_prs.reopen(issue)

            if self.mode is self.ISSUE_DETAIL:
                self.issue_detail(issue)
        elif key == KEY_BACK:
            if self.mode is self.PR_DIFF:
                pr = self.ui.get_focused_item()
                self.pull_request_detail(pr)
            elif self.mode in [self.ISSUE_DETAIL, self.PR_DETAIL]:
                self.issue_list()
        elif key == KEY_DETAIL:
            if self.mode is self.ISSUE_LIST:
                issue_or_pr = self.ui.get_focused_item()

                if is_issue(issue_or_pr):
                    self.issue_detail(issue_or_pr)
                elif is_pull_request(issue_or_pr):
                    self.pull_request_detail(issue_or_pr)
        elif key == KEY_EDIT:
            item = self.ui.get_focused_item()

            if item is None:
                return

            if is_pull_request(item):
                item = item.issue

            # In case you aren't the owner of the repo, you are only allowed to
            # edit things that you created.
            if self.repo.owner != self.user and item.user != self.user:
                # TODO: beep
                return

            if is_issue(item):
                self.edit_issue(item)
            else:
                self.edit_body(item)
        elif key == KEY_COMMENT:
            item = self.ui.get_issue_or_pr()

            if item is None:
                return

            if is_pull_request(item):
                issue = item.issue
                self.comment_issue(item.issue, pull_request=item)
            else:
                self.comment_issue(item)
        elif key == KEY_DIFF:
            if self.mode is self.PR_DETAIL:
                pr = self.ui.get_focused_item()
                self.diff(pr)
        elif key == KEY_BROWSER:
            item = self.ui.get_focused_item()
            if hasattr(item, '_api'):
                webbrowser.open(item.html_url)
        elif key == KEY_QUIT:
            raise ExitMainLoop

    def edit_issue(self, issue):
        title_and_body = '\n'.join([issue.title, issue.body])
        issue_text = self.spawn_editor(title_and_body)

        if issue_text is None:
            # TODO: cancelled
            return

        contents = unlines(issue_text)
        title, *body = contents

        if not title:
            # TODO: incorrect input, at least a title is needed
            return
        body = lines(body)

        issue.edit(title=title, body=body)

        if self.mode is self.ISSUE_LIST:
            # TODO: focus
            self.issue_list()
        elif self.mode is self.ISSUE_DETAIL:
            self.issue_detail(issue)

    # TODO
    def edit_pull_request(self, pr):
        pass

    def edit_body(self, item):
        text = self.spawn_editor(item.body)

        if text is None:
            # TODO: cancelled
            return

        # TODO: ui must be updated!
        item.edit(text)

    def comment_issue(self, issue, *, pull_request=False):
        issue_thread = format_issue_thread(issue)

        comment_text = self.spawn_editor('\n'.join(issue_thread))

        if comment_text is None:
            # TODO: cancelled
            return

        if not comment_text:
            # TODO: A empty comment is invalid input
            return

        issue.create_comment(comment_text)

        if pull_request:
            self.pull_request_detail(pull_request)
        else:
            self.issue_detail(issue)

    def spawn_editor(self, help_text=None):
        """
        Open a editor with a temporary file containing ``help_text``.

        If the exit code is 0 the text from the file will be returned.

        Otherwise, ``None`` is returned.
        """
        text = '' if help_text is None else help_text

        tmp_file = tempfile.NamedTemporaryFile(mode='w+',
                                            suffix='.markdown',
                                            delete=False)
        tmp_file.write(text)
        tmp_file.close()

        fname = tmp_file.name

        self.loop.screen.stop()

        return_code = subprocess.call([os.getenv('EDITOR', 'vim'), fname])

        self.loop.screen.start()

        if return_code == 0:
            with open(fname, 'r') as f:
                contents = f.read()

        if return_code != 0:
            return None
        else:
            return strip_comments(contents)

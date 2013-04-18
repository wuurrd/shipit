import itertools
from abc import ABCMeta, abstractmethod
import concurrent.futures

from urwid import MonitoredList
import github3.issues as issues
import github3.pulls as pulls


def is_issue(item):
    return isinstance(item, issues.Issue) and item.pull_request is None


def is_open(item):
    if hasattr(item, "state"):
        return item.state == "open"


def is_closed(item):
    if hasattr(item, "state"):
        return item.state == "closed"


def is_pull_request(item):
    return isinstance(item, pulls.PullRequest)


def is_comment(item):
    return isinstance(item, (issues.comment.IssueComment, pulls.ReviewComment))


class DataSource(metaclass=ABCMeta):
    """A source of data with the notion of updates."""
    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def __iter__(self):
        pass


class DataFilter(metaclass=ABCMeta):
    """
    A class that represents a filter over an iterable. Filters can be composed.
    """
    @abstractmethod
    def filter(self, iterable):
        pass

    @staticmethod
    def compose(*filters):
        """
        Takes an arbitrary number of filter as positional arguments and return
        a function that takes an iterable and creates a filtered iterable that
        passes all the filters.
        """
        def combined(iterable):
            for f in filters:
                iterable = f.filter(iterable)
            return iterable
        return combined


class IssueSource(DataSource):
    def __init__(self, repo):
        self.repo = repo
        self.issues = []
        self.open_bootstrapped = False
        self.closed_bootstrapped = False

    def fetch_open(self):
        open_issues = filter(is_issue, self.repo.iter_issues(state='open'))
        self.issues.extend([i for i in open_issues if i not in self.issues])

    def fetch_closed(self):
        closed_issues = filter(is_issue, self.repo.iter_issues(state='closed'))
        self.issues.extend([i for i in closed_issues if i not in self.issues])

    def update(self):
        raise NotImplementedError

    def __iter__(self):
        return itertools.chain(self.iter_open(), self.iter_closed())

    def iter_open(self):
        if not self.open_bootstrapped:
            self.open_bootstrapped = True
            self.fetch_open()
        return filter(is_open, self.issues)

    def iter_closed(self):
        if not self.closed_bootstrapped:
            self.closed_bootstrapped = True
            self.fetch_closed()
        return filter(is_closed, self.issues)


class PullRequestSource(DataSource):
    def __init__(self, repo):
        self.repo = repo
        self.pulls = []
        self.bootstrapped = False

    def update(self):
        pulls = self.repo.iter_pulls()
        for p in pulls:
            setattr(p, 'issue', self.repo.issue(p.number))
            if p not in self.pulls:
                self.pulls.append(p)

    def __iter__(self):
        if not self.bootstrapped:
            self.update()
            self.bootstrapped = True
        return iter(self.pulls)


class IssuesAndPullRequests(MonitoredList):
    """
    The main data structure that powers ``shipit``. It inherits from
    ``urwid.MonitoredList`` so the widget that is displaying it reacts to
    changes on the list.

    It tracks which issues/pulls are being shown.
    """
    OPEN_ISSUES = 0
    CLOSED_ISSUES = 1
    PULL_REQUESTS = 2

    def __init__(self, repo):
        self.repo = repo
        # Data sources
        self._issues_source = IssueSource(repo)
        self._prs_source = PullRequestSource(repo)
        # Filters
        self._filters = []
        # What's currently holding
        self.showing = self.OPEN_ISSUES

    # TODO: Asynchronous operations

    def close(self, issue):
        issue.close()
        if self.showing == self.OPEN_ISSUES:
            self.remove(issue)

    def reopen(self, issue):
        issue.reopen()
        if self.showing == self.CLOSED_ISSUES:
            self.remove(issue)

    # TODO: merge PR

    # Filters

    def show_all(self):
        pass

    def show_created_by(self, user):
        pass

    def show_assigned_to(self, user):
        pass

    def show_mentioning(self, user):
        pass

    def show_open_issues(self, **kwargs):
        self.showing = self.OPEN_ISSUES
        del self[:]
        self._append_open_issues()

    def show_closed_issues(self, **kwargs):
        self.showing = self.CLOSED_ISSUES
        del self[:]
        self._append_closed_issues()

    def show_pull_requests(self, **kwargs):
        self.showing = self.PULL_REQUESTS
        del self[:]
        self._append_pull_requests()

    # TODO
    #def update(self):
        #pass

    def _append_open_issues(self):
        for i in self._issues_source.iter_open():
            if i not in self:
                self.append(i)

    def _append_closed_issues(self):
        for i in self._issues_source.iter_closed():
            if i not in self:
                self.append(i)

    def _append_pull_requests(self):
        for pr in self._prs_source:
            if pr not in self:
                self.append(pr)

    def filter_by_labels(self, labels):
        if self.showing in [self.OPEN_ISSUES, self.CLOSED_ISSUES]:
            for i in self[:]:
                has_labels = [label in i.labels for label in labels]
                if not any(has_labels):
                    self.remove(i)
        else:
            for pr in self[:]:
                i = pr.issue
                has_labels = [label in i.labels for label in labels]
                if not any(has_labels):
                    self.remove(pr)

    def clear_label_filters(self):
        if self.showing == self.OPEN_ISSUES:
            self.show_open_issues()
        elif self.showing == self.CLOSED_ISSUES:
            self.show_closed_issues()
        else:
            self.show_pull_requests()

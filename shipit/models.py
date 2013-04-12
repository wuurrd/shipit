import concurrent.futures

from urwid import MonitoredList
import github3.issues as issues
import github3.pulls as pulls


def is_issue(item):
    return isinstance(item, issues.Issue)


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


class IssuesAndPullRequests(MonitoredList):
    """
    The main data structure that powers ``shipit``. It inherits from
    ``urwid.MonitoredList`` so the widget that is displaying it reacts to
    changes on the list.

    It tracks which issues are being shown as well as the ones that aren't and
    the pull requests for the repository.
    """
    OPEN_ISSUES = 0
    CLOSED_ISSUES = 1
    PULL_REQUESTS = 2

    def __init__(self, repo):
        self._issues = []
        self._prs = []
        self._pr_issues = {}
        self.repo = repo
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

    def fetch_all(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            executor.submit(self.fetch_open_issues)
            executor.submit(self.fetch_closed_issues)
            executor.submit(self.fetch_pull_requests)

    # TODO
    def update(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for i in self:
                executor.submit(i.refresh)
            #executor.submit(self.fetch_open_issues)
            #executor.submit(self.fetch_closed_issues)
            #executor.submit(self.fetch_pull_requests)

    def fetch_pull_requests(self):
        # TODO: don't duplicate
        print("Fetching prs")
        for p in self.repo.iter_pulls():
            p.issue = self._pr_issues[p.number]
            self._prs.append(p)
        print("Fetched prs")

    def fetch_open_issues(self):
        # TODO: don't duplicate
        print("Fetching open issues")
        for i in self.repo.iter_issues():
            if i.pull_request:
                self._pr_issues[i.number] = i
            else:
                self._issues.append(i)
        print("Fetched open issues")

    def fetch_closed_issues(self):
        # TODO: don't duplicate
        print("Fetching closed issues")
        self._issues.extend([i for i in self.repo.iter_issues(state='closed')])
        print("Fetched closed issues")

    def _append_open_issues(self, future=None):
        for i in filter(is_open, self._issues):
            if i not in self:
                self.append(i)

    def _append_closed_issues(self, future=None):
        for i in filter(is_closed, self._issues):
            if i not in self:
                self.append(i)

    def _append_pull_requests(self, future=None):
        for pr in self._prs:
            if pr not in self:
                self.append(pr)

    def filter_by_labels(self, labels):
        if self.showing in [self.OPEN_ISSUES, self.CLOSED_ISSUES]:
            for i in self[:]:
                has_labels = [label in i.labels for label in labels]
                if not any(has_labels):
                    self.remove(i)
        else:
            # TODO: filter pr's looking at their corresponding issues
            pass

    def clear_label_filters(self):
        if self.showing == self.OPEN_ISSUES:
            self.show_open_issues()
        elif self.showing == self.CLOSED_ISSUES:
            self.show_closed_issues()
        else:
            self.show_pull_requests()

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

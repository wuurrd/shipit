# -*- coding: utf-8 -*-

"""
shipit.ui
~~~~~~~~~

User interface elements.
"""

import time
from calendar import timegm

import urwid
from x256 import x256

from .config import (
    DIVIDER,

    KEY_OPEN_ISSUE, KEY_REOPEN_ISSUE, KEY_CLOSE_ISSUE, KEY_BROWSER, KEY_DETAIL,
    KEY_COMMENT, KEY_EDIT, KEY_QUIT, KEY_BACK, KEY_DIFF
)
from .events import trigger
from .models import is_issue, is_pull_request, is_comment, is_open
from .func import unlines

VI_KEYS = {
    'j': 'down',
    'k': 'up',
    'h': 'left',
    'l': 'right',

    'ctrl u': 'page up',
    'ctrl d': 'page down',

    #'g': 'home',
    #'G': 'end',
}

ISSUE_LIST_KEYS = [
    (KEY_DETAIL, " View in detail "),
    (KEY_BROWSER, " Open in browser "),
    (KEY_OPEN_ISSUE, " Open issue "),
    (KEY_CLOSE_ISSUE, " Close "),
    (KEY_REOPEN_ISSUE, " Reopen "),
    (KEY_COMMENT, " Comment "),
    (KEY_EDIT, " Edit "),
    (KEY_QUIT, " Quit "),
]

ISSUE_DETAIL_KEYS = [
    (KEY_BACK, " Go back "),
    (KEY_CLOSE_ISSUE, " Close issue "),
    (KEY_REOPEN_ISSUE, " Reopen issue "),
    (KEY_COMMENT, " Comment on issue "),
    (KEY_EDIT, " Edit issue or comment "),
    (KEY_QUIT, " Quit "),
]

PR_DETAIL_KEYS = [
    (KEY_BACK, " Go back "),
    (KEY_DIFF, " View diff "),
    (KEY_QUIT, " Quit "),
]

def issue_title(issue):
    text = urwid.Text([("title", issue.title)])
    return urwid.Padding(text, left=0, right=3)


def issue_number(issue):
    return ("number", "#{}".format(issue.number))


def pull_request_number(pr):
    return [('green_text', '+'),
            ('red_text', '-'),
            ("number", "#{}".format(pr.number))]


def issue_marker(issue):
    return ('green_text', '☑') if issue.is_closed() else ('red_text', '☐')


def pull_request_marker(pr):
    return ('green_text', 'Y') if pr.is_merged() else ('red_text', 'o')


def issue_comments(issue):
    if not issue.comments:
        return urwid.Text("")

    if issue.comments == 1:
        text = "1 comment"
    else:
        text = "%s comments" % issue.comments

    return urwid.Text(("text", text))


def issue_author(issue):
    return urwid.Text([("username", str(issue.user)),
                       ("text", " opened this issue")])


def issue_time(issue):
    return urwid.Text([("time", time_since(issue.created_at))],
                      align='right',)


def issue_milestone(issue):
    if not issue.milestone:
        return urwid.Text("")

    text = "Milestone: %s" % issue.milestone.title
    return  urwid.Text([("milestone", text)],
                       align='right',)


def issue_assignee(issue):
    if not issue.assignee:
        return urwid.Text("")

    username = "%s" % str(issue.assignee)

    return urwid.Text([("username", username),  ("assignee", " is assigned")])


def pr_author(pr):
    return urwid.Text([("username", str(pr.user)),
                       ("text", " opened this pull request")])


def pr_comments(pr):
    return issue_comments(pr.issue)


def pr_commits(pr):
    commits = len([_ for _ in pr.iter_commits()])
    if commits == 1:
        text = "1 commit"
    else:
        text = "%s commits" % commits

    return urwid.Text(("text", text))


def pr_additions(pr):
    additions = sum([file.additions for file in pr.iter_files()])
    return urwid.Text([("green_text", "+"), ("text", " %s additions" % additions)])


def pr_deletions(pr):
    deletions = sum([file.deletions for file in pr.iter_files()])
    return urwid.Text([("red_text", "-"), ("text", " %s deletions" % deletions)])


def pr_diff(pr):
    raw_diff = bytes.decode(pr.diff())[2:]
    return raw_diff[:-1]



pr_title = issue_title
#pr_assignee = issue_assignee
#pr_milestone = issue_assignee
pr_time = issue_time


def timestamp_from_datetime(datetime):
    return timegm(datetime.utctimetuple())


def time_since(datetime):
    # This code is borrowed from `python-twitter` library
    fudge = 1.25
    delta = float(time.time() - timestamp_from_datetime(datetime))

    if delta < (1 * fudge):
        return "a second ago"
    elif delta < (60 * (1 / fudge)):
        return "%d seconds ago" % (delta)
    elif delta < (60 * fudge):
        return "a minute ago"
    elif delta < (60 * 60 * (1 / fudge)):
        return "%d minutes ago" % (delta / 60)
    elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
        return "an hour ago"
    elif delta < (60 * 60 * 24 * (1 / fudge)):
        return "%d hours ago" % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
        return "a day ago"
    else:
        return "%d days ago" % (delta / (60 * 60 * 24))


def create_label_attr(label):
    # TODO: sensible foreground color
    bg = "h%s" % x256.from_hex(label.color)
    return urwid.AttrSpec("black", bg)


def create_label_widget(label):
    attr = create_label_attr(label)

    label_name = " ".join(["", label.name, ""])

    return urwid.Text((attr, label_name))


def box(widget):
    return urwid.AttrMap(urwid.LineBox(widget), "line", "focus")


def make_divider(divider=DIVIDER):
    return urwid.AttrMap(urwid.Divider(divider), "divider")


def make_vertical_divider():
    return urwid.Padding(urwid.SolidFill(" "), left=1, right=1)



class ViMotionListBox(urwid.ListBox):
    def __init__(self, arg, selectable=True):
        super(ViMotionListBox, self).__init__(arg)
        self._selectable = selectable

    def keypress(self, size, key):
        key = VI_KEYS.get(key, key)
        return super(ViMotionListBox, self).keypress(size, key)

    def selectable(self):
        return self._selectable


class Header(urwid.WidgetWrap):
    def __init__(self, repo):
        self.repo = repo
        super(Header, self).__init__(urwid.Text("shipit"))

    @staticmethod
    def _make_text(text):
        return urwid.Text(text, align='center')

    def _owner_and_repo(self):
        owner = ("username", str(self.repo.owner))
        repo = ("text", self.repo.name)
        return [owner, " / ", repo]

    def issues_and_pulls(self):
        self._w = self._make_text(self._owner_and_repo())

    def issue(self, issue):
        text = self._owner_and_repo()
        text.extend([" ─ ",
                     ("text", "Issue "),
                     ("number", "#%s" % issue.number),
                     " ",
                     ("title", issue.title)])
        self._w = self._make_text(text)

    def pull_request(self, pr):
        text = self._owner_and_repo()
        text.extend([" ─ ",
                     ("text", "Pull Request "),
                     ("number", "#%s" % pr.number),
                     " ",
                     ("title", pr.title)])
        self._w = self._make_text(text)


class Footer(urwid.WidgetWrap):
    def __init__(self):
        super(Footer, self).__init__(urwid.Text(""))

    def issue_list(self):
        self._w = self._build_widget(ISSUE_LIST_KEYS)

    def issue_detail(self):
        self._w = self._build_widget(ISSUE_DETAIL_KEYS)

    def pr_detail(self):
        self._w = self._build_widget(PR_DETAIL_KEYS)

    def _build_widget(self, key_description):
        text = self._build_text_list(key_description)
        return urwid.Pile([make_divider("·"),
                           urwid.Text(text, align="center")])

    def _build_text_list(self, key_description):
        text = []
        for key, description in key_description:
            text.extend([("key", key), ("text", description)])
        return text


class UI(urwid.WidgetWrap):
    """
    Creates a curses interface for the program, providing functions to draw
    all the components of the UI.
    """
    def __init__(self, repo):
        self.repo = repo
        self.views = {}

        header = Header(repo)
        footer = Footer()

        # body
        body = urwid.Text("shipit")

        # footer
        self.frame = urwid.Frame(body, header=header, footer=footer)

        super(UI, self).__init__(self.frame)

    # -- API ------------------------------------------------------------------

    def get_focused_item(self, parent_over_comment=False, *args):
        """
        Return the currently focused item when a Issue or Pull Request is
        focused.

        If the keyword arg ``parent_over_comment`` is ``True``, the original
        Issue or Pull Request will be returned instead of the comment when a
        comment is focused.
        """
        body = self.frame.body

        widget = body.focus.focus

        if isinstance(body, Diff):
            focused = body.pr
        elif not widget:
            focused = None
        elif isinstance(widget, PRDetailWidget):
            focused = widget.pr
        elif isinstance(widget, PRCommentWidget):
            focused = widget.pr if parent_over_comment else widget.comment
        elif isinstance(widget, IssueCommentWidget):
            focused = widget.issue if parent_over_comment else widget.comment
        else:
            focused = widget.issue if hasattr(widget, 'issue') else None

        focused_is_valid = any([is_issue(focused),
                                is_pull_request(focused),
                                is_comment(focused)])

        return focused if focused_is_valid else None

    def get_issue(self):
        """Return a issue if it's focused, otherwise return ``None``."""
        issue = self.get_focused_item(parent_over_comment=True)
        return issue if is_issue(issue) else None

    def get_issue_or_pr(self):
        """
        Return a issue or pull request if it's focused, otherwise return
        ``None``.
        """
        item = self.get_focused_item(parent_over_comment=True)
        return item if is_issue(item) or is_pull_request(item) else None

    # -- Modes ----------------------------------------------------------------

    def issues_and_pulls(self, issues_and_pulls):
        self.frame.header.issues_and_pulls()
        self.frame.footer.issue_list()

        if isinstance(self.frame.body, ListWidget):
            self.frame.body.reset_list(issues_and_pulls)
            return

        if "issues" in self.views:
            body = self.views["issues"]
        else:
            body = ListWidget(self.repo, issues_and_pulls)
            self.views["issues"] = body

        self.frame.set_body(body)

    def issue(self, issue):
        self.frame.header.issue(issue)
        self.frame.footer.issue_detail()

        key = "issue.%s" % issue.number
        if key in self.views:
            body = self.views[key]
        else:
            body = issue_detail(issue)
            self.views[key] = body

        self.frame.set_body(body)

    def pull_request(self, pr):
        """Render a detail view for the `pr` pull request."""
        self.frame.header.pull_request(pr)
        self.frame.footer.pr_detail()

        self.frame.body = pull_request_detail(pr)
        self.frame.set_body(self.frame.body)

    def diff(self, pr):
        self.frame.body = Diff(pr)
        self.frame.set_body(self.frame.body)


class IssueListWidget(urwid.WidgetWrap):
    """
    Widget containing a issue's basic information, meant to be rendered on a
    list.
    """
    def __init__(self, issue):
        self.issue = issue

        widget = self._build_widget(issue)

        super(IssueListWidget, self).__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        title = issue_title(issue)
        labels = cls._create_label_widgets(issue)
        title_labels = urwid.Columns([('weight', 0.7, title),
                                      ('weight', 0.3, labels)])

        author = issue_author(issue)
        time = issue_time(issue)
        author_time = urwid.Columns([author, time])

        widget_list = [title_labels, author_time]

        if issue.assignee or issue.milestone:
            assignee = issue_assignee(issue)
            milestone = issue_milestone(issue)
            assignee_milestone = urwid.Columns([assignee, milestone])
            widget_list.append(assignee_milestone)

        if issue.comments:
            widget_list.append(issue_comments(issue))

        number_and_marker = urwid.Text([issue_number(issue), 3 * ' ', issue_marker(issue)])
        pile = urwid.Pile(widget_list)
        info = urwid.Columns([(9, number_and_marker), pile])

        return box(info)

    @classmethod
    def _create_label_widgets(cls, issue):
        label_widgets = [create_label_widget(label) for label in issue.labels]
        return urwid.Pile(label_widgets)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class PRListWidget(IssueListWidget):
    """
    Widget containing a Pull Requests's basic information, meant to be rendered
    on a list.
    """
    @classmethod
    def _build_widget(cls, pr):
        """Return a widget for the ``pr``."""
        title = pr_title(pr)

        author = pr_author(pr)
        time = pr_time(pr)
        author_time = urwid.Columns([author, time])

        widget_list = [title,
                       author_time,]

        comments = pr_comments(pr)
        if comments:
            widget_list.append(comments)

        pile = urwid.Pile(widget_list)
        number_and_marker = urwid.Text([pull_request_number(pr),
                                        3 * ' ',
                                        pull_request_marker(pr)])
        widget = urwid.Columns([(12, number_and_marker), pile])


        return box(widget)


def issue_detail(issue):
    comments = [IssueCommentWidget(issue, comment) for comment in issue.iter_comments()]
    comments.insert(0, IssueDetailWidget(issue))

    thread = ViMotionListBox(urwid.SimpleListWalker(comments))

    info_widgets = []
    if is_open(issue):
        state_indicator = urwid.Text(("green", " Open "), align='center')
    else:
        state_indicator = urwid.Text(("red", " Closed "), align='center')

    info_widgets.append(state_indicator)
    info_widgets.append(issue_comments(issue))

    label_widgets = [make_divider(), Legend("Labels"), urwid.Text("")]
    label_widgets.extend([create_label_widget(label) for label in issue.labels])

    info_widgets.extend(label_widgets)

    info = ViMotionListBox(urwid.SimpleListWalker(info_widgets),
                           selectable=False)
    vertical_divider = make_vertical_divider()

    widget = urwid.Columns([('weight', 0.8, thread),
                            (3, vertical_divider),
                            ('weight', 0.2, info)])

    return widget


def pull_request_detail(pr):
    comments = [PRCommentWidget(pr, comment) for comment in pr.issue.iter_comments()]
    comments.insert(0, PRDetailWidget(pr))

    thread = ViMotionListBox(urwid.SimpleListWalker(comments))

    info_widgets = []
    if is_open(pr):
        state_indicator = urwid.Text(("green", " Open "), align='center')
    else:
        state_indicator = urwid.Text(("red", " Closed "), align='center')

    info_widgets.append(state_indicator)
    info_widgets.append(pr_commits(pr))

    additions = pr_additions(pr)
    deletions = pr_deletions(pr)

    info_widgets.append(additions)
    info_widgets.append(deletions)

    info = ViMotionListBox(urwid.SimpleListWalker(info_widgets),
                           selectable=False)

    vertical_divider = make_vertical_divider()

    widget = urwid.Columns([('weight', 0.8, thread),
                            (3, vertical_divider),
                            ('weight', 0.2, info)])

    return widget


def issue_list(issues):
    for issue in issues:
        if is_issue(issue):
            yield IssueListWidget(issue)
        elif is_pull_request(issue):
            yield PRListWidget(issue)


class ListWidget(urwid.Columns):
    """
    A widget that represents a list of issues and Pull Requests, along with
    controls for sorting and filtering the aforementioned entities.
    """
    def __init__(self, repo, items):
        issue_widgets = [w for w in issue_list(items)]

        self.issues = ViMotionListBox(urwid.SimpleListWalker(issue_widgets))
        vertical_divider = make_vertical_divider()
        self.controls = Controls(repo, items)

        super(ListWidget, self).__init__(
            [('weight', 0.8, self.issues),
             (3, vertical_divider),
             ('weight', 0.2, self.controls),])

    def reset_list(self, items):
        widgets = [w for w in issue_list(items)]
        list_walker = self.issues.body
        del list_walker[:]
        list_walker.extend(widgets)


class Controls(ViMotionListBox):
    # TODO: Milestone filter
    def __init__(self, repo, issues):
        self.repo = repo
        self.issues = issues

        widgets = self._build_widgets()

        super(Controls, self).__init__(urwid.SimpleListWalker(widgets))

    def _build_widgets(self):
        controls = []
        # Open/Closed/Pull Request
        state_filters = []
        controls.extend([OpenIssuesFilter(state_filters),
                         ClosedIssuesFilter(state_filters),
                         PullRequestsFilter(state_filters),
                         make_divider()])
        # Assignation filters
        filters = []
        controls.extend([Legend("Show"),
                         br,
                         AllFilter(filters),
                         CreatedFilter(filters),
                         AssignedFilter(filters),
                         MentioningFilter(filters),])
        # Labels
        labels = LabelFiltersWidget(label for label in self.repo.iter_labels())
        controls.extend([br, labels])

        return controls

    def get_focused(self):
        pass


class Legend(urwid.Text):
    def __init__(self, text):
        super(Legend, self).__init__(("legend", text))

    def selectable(self):
        return False


class RadioButtonWrap(urwid.WidgetWrap):
    def __init__(self, filters, label, check=None):
        self.chec = check

        widget = urwid.RadioButton(filters, label)

        urwid.connect_signal(widget, "change", self.on_change)

        super(RadioButtonWrap, self).__init__(urwid.AttrWrap(widget, "default", "focus"))


    def on_change(self, checkbox, new_state):
        if new_state and callable(self.on_check):
            self.on_check()

    def on_check(self):
        pass


class AllFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(AllFilter, self).__init__(filters, "All")

    def on_check(self):
        trigger("show_all")


class CreatedFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(CreatedFilter, self).__init__(filters, "Created by you")

    def on_check(self):
        trigger("show_created_by_you")


class AssignedFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(AssignedFilter, self).__init__(filters, "Assigned to you")

    def on_check(self):
        trigger("show_assigned_to_you")


class MentioningFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(MentioningFilter, self).__init__(filters, "Mentioning you")

    def on_check(self):
        trigger("show_mentioning_you")


class OpenIssuesFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(OpenIssuesFilter, self).__init__(filters, "Open")

    def on_check(self):
        trigger("show_open_issues")


class ClosedIssuesFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(ClosedIssuesFilter, self).__init__(filters, "Closed")

    def on_check(self):
        trigger("show_closed_issues")


class PullRequestsFilter(RadioButtonWrap):
    def __init__(self, filters):
        super(PullRequestsFilter, self).__init__(filters, "Pull Requests")

    def on_check(self):
        trigger("show_pull_requests")


class LabelWidget(urwid.WidgetWrap):
    """Represent a label."""
    def __init__(self, label):
        self.label = label
        self.checkbox = urwid.CheckBox(" ")

        checkbox = urwid.AttrMap(self.checkbox, "default", "focus")
        label_widget = create_label_widget(label)
        widget = urwid.Columns([(5, checkbox), label_widget])

        super(LabelWidget, self).__init__(widget)


class LabelFiltersWidget(urwid.WidgetWrap):
    """
    A widget that renders checkboxes with the labels of the repo, meant to be
    used for filtering by label.

    When one or more labels are selected, a ``filter_by_labels`` event will be
    triggered. When all the labels are deselected, a ``clear_label_filters``
    event will be triggered.
    """
    def __init__(self, labels):
        # Legend
        widgets = [Legend("Filter by label"), br]
        # Checkboxes
        self.label_widgets = [LabelWidget(label) for label in labels]
        widgets.extend(self.label_widgets)
        widget = urwid.Pile(widgets)

        for w in self.label_widgets:
            urwid.connect_signal(w.checkbox, 'change', self.on_change, w.label)

        super(LabelFiltersWidget, self).__init__(widget)

    def on_change(self, checkbox, new_state, label):
        # Have to use ``id`` here since Checkbox widgets don't implement __eq__
        widgets = [w for w in self.label_widgets if id(w.checkbox) != id(checkbox)]

        labels = [w.label for w in widgets]
        states = [w.checkbox.get_state() for w in widgets]

        labels.append(label)
        states.append(new_state)

        if any(states):
            # Get the checked labels and trigger ``filter_by_labels``
            checked_labels = [label for label, state in zip(labels, states) if state]
            trigger("filter_by_labels", checked_labels)
        else:
            # They are all unchecked
            trigger("clear_label_filters")




class IssueDetailWidget(urwid.WidgetWrap):
    """
    A widget for rendering an issue in detail . It includes all the information
    regarding the issue.

    Includes the following information:

         ---------------------------------
        |{title}                          |
        |{user} opened this issue {time}  |
        |{assignee}           {milestone} |
        |{participants}                   |
        |---------------------------------|
        |{body}                           |
         ---------------------------------
    """
    # TODO: participants
    BODY_FORMAT = "{body}"

    def __init__(self, issue):
        self.issue = issue
        widget = self._build_widget(issue)
        super(IssueDetailWidget, self).__init__(widget)

    @classmethod
    def _build_widget(cls, issue):
        """Return a widget for the ``issue``."""
        header = cls._create_header_widget(issue)
        if issue.body_text:
            body = cls._create_body_widget(issue)
            divider = make_divider()
            widget = urwid.Pile([header, divider, body])
        else:
            widget = header

        return box(widget)

    @classmethod
    def _create_header_widget(cls, issue):
        title = issue_title(issue)
        labels = urwid.Columns([create_label_widget(label) for label in issue.labels])
        title_labels = urwid.Columns([(60, title), labels])

        author = issue_author(issue)
        time = issue_time(issue)
        author_time = urwid.Columns([author, time])

        assignee = issue_assignee(issue)
        milestone = issue_milestone(issue)
        assignee_milestone = urwid.Columns([assignee, milestone])

        widget = urwid.Pile([title_labels, author_time, assignee_milestone])

        return widget

    @classmethod
    def _create_body_widget(cls, issue):
        text = cls.BODY_FORMAT.format(
            body=issue.body_text,
        )
        widget = urwid.Text(["\n", ("body", text)])
        return urwid.Padding(widget, left=2, right=2)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key



class IssueCommentWidget(urwid.WidgetWrap):
    def __init__(self, issue, comment):
        self.issue = issue
        self.comment = comment

        widget = self._build_widget(comment)

        super(IssueCommentWidget, self).__init__(widget)

    @classmethod
    def _build_widget(cls, comment):
        """Return the wrapped widget."""
        header = cls._create_header(comment)
        body = cls._create_body(comment)

        divider = make_divider()

        widget = urwid.Pile([header, divider, body])

        return box(widget)

    @classmethod
    def _create_header(cls, comment):
        """
        Return the header text for the comment associated with this widget.
        """
        author = cls.comment_author(comment)
        time = cls.comment_time(comment)

        return urwid.Columns([author, time])

    @classmethod
    def _create_body(cls, comment):
        widget = urwid.Text(("body", comment.body_text))
        return urwid.Padding(widget, left=2, right=2)

    @staticmethod
    def comment_author(comment):
        return urwid.Text([("username", str(comment.user)),
                           ("text", " commented")],)

    @staticmethod
    def comment_time(comment):
        return urwid.Text(("time", time_since(comment.created_at)),
                          align='right',)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class PRDetailWidget(urwid.WidgetWrap):
    """
    Includes the following information:

         ---------------------------------
        |{title}                          |
        |{user} opened this pr     {time} |
        |{assignee}           {milestone} |
        |{participants}                   |
        |---------------------------------|
        |{body}                           |
         ---------------------------------
        |{merge_status}                   |
         ---------------------------------
    """
    # TODO: participants
    def __init__(self, pr):
        self.pr = pr
        widget = self._build_widget(pr)
        super(PRDetailWidget, self).__init__(widget)

    @classmethod
    def _build_widget(cls, pr):
        """Return a widget for the ``pr``."""
        title = pr_title(pr)

        author = pr_author(pr)
        time = pr_time(pr)
        author_time = urwid.Columns([author, time])

        widget_list = [title, author_time]

        #assignee = pr_assignee(pr)
        #milestone = pr_milestone(pr)
        #assignee_milestone = urwid.Columns([assignee, milestone])
        divider = make_divider()

        body = cls._create_body_widget(pr)

        if pr.body:
            widget_list.extend([divider, body])

        # FIXME: is this always false? maybe a bug in the library
        if pr.mergeable:
            mergeable = urwid.Text(("green", "Can be automatically merged"))
        else:
            mergeable = urwid.Text(("red", "Can't be automatically merged"))
        widget_list.extend([divider, mergeable])

        widget = urwid.Pile(widget_list)

        return box(widget)

    @classmethod
    def _create_body_widget(cls, pr):
        widget = urwid.Text(["\n", ("body", pr.issue.body_text)])
        return urwid.Padding(widget, left=2, right=2)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


# TODO: Base CommentWidget
class PRCommentWidget(IssueCommentWidget):
    def __init__(self, pr, comment):
        self.pr = pr

        super(PRCommentWidget, self).__init__(pr.issue, comment)


class Diff(ViMotionListBox):
    def __init__(self, pr):
        self.pr = pr
        self.diff = pr_diff(pr)
        super(Diff, self).__init__(
            urwid.SimpleListWalker(
                [l for l in self._build_lines(self.diff)]))

    @staticmethod
    def _build_lines(diff):
        for line in unlines(diff):
            if line.startswith("ff"):
                yield urwid.Text(("text", line))
            elif line.startswith("index"):
                yield urwid.Text(("text", line))
            elif line.startswith("@@"):
                yield urwid.Text(("cyan_text", line))
            elif line.startswith("+++"):
                yield urwid.Text(("text", line))
            elif line.startswith("+"):
                yield urwid.Text(("green_text", line))
            elif line.startswith("---"):
                yield urwid.Text(("text", line))
            elif line.startswith("-"):
                yield urwid.Text(("red_text", line))
            else:
                yield urwid.Text(("code", line))


br = Legend("")

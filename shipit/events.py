# -*- coding: utf-8 -*-

"""
shipit.events
~~~~~~~~~~~~~

Poor man's pub-sub mechanism.
"""

EVENTS = [
    "show_all",
    "show_created_by_you",
    "show_assigned_to_you",
    "show_mentioning_you",

    "show_open_issues",
    "show_closed_issues",
    "show_pull_requests",

    "filter_by_labels",
    "clear_label_filters",
]


SUBSCRIBED = {event: [] for event in EVENTS}


def trigger(event, *args, **kwargs):
    if event in EVENTS:
        for callback in SUBSCRIBED[event]:
            callback(*args, **kwargs)
    else:
        raise ValueError("{} is not a valid event.".format(event))


def on(event, callback):
    if event in EVENTS:
        SUBSCRIBED[event].append(callback)
    else:
        raise ValueError("{} is not a valid event.".format(event))

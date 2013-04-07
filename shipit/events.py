"""
shipit.events
~~~~~~~~~~~~~

Poor man's pub-sub mechanism.
"""

EVENTS = [
 'show_open_issues',
 'show_closed_issues',
 'show_pull_requests',

 'filter_by_labels',
 'clear_label_filters',
]


SUBSCRIBED = dict([(event,[]) for event in EVENTS])

def trigger(event, *args, **kwargs):
    if event in EVENTS:
        for callback in SUBSCRIBED[event]:
            callback(*args, **kwargs)
    else:
        raise ValueError("%s is not a valid event." % event)

def on(event, callback):
    if event in EVENTS:
        SUBSCRIBED[event].append(callback)
    else:
        raise ValueError("%s is not a valid event." % event)



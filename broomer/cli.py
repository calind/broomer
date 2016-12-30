# pylint: disable=missing-docstring
# -*- coding: utf-8 -*-
# vim: ft=python:sw=4:ts=4:sts=4:et:
import re
import maya
import pystache
import yaml

from requests.auth import HTTPBasicAuth
from zipa import api_github_com as github  # pylint: disable=no-name-in-module


def human_to_datetime(time):
    if not time:
        return None
    return maya.when(time).datetime(to_timezone='UTC').replace(microsecond=0)


class Comment(object):
    def __init__(self, issue, **comment):
        self.data = comment
        self.issue = issue
        self.author = comment.get('user').get('login')
        self.body = comment.get('body')
        self.updated_at = human_to_datetime(comment.get('updated_at'))
        self.created_at = human_to_datetime(comment.get('created_at'))

    def __unicode__(self):
        return ('{author}@{issue}/comment-{id}'.format(
            id=self.data.get('id'), issue=self.issue, author=self.author
        ))

    def __str__(self):
        return self.__unicode__()


class Issue(object):
    def __init__(self, **issue):
        self.data = issue
        self.number = issue.get('number')
        self.title = issue.get('title')
        self.body = issue.get('body')
        self.milestone = issue.get('milesone', {}).get('title')
        self.author = issue.get('user').get('login')
        self.pull_request = bool(issue.get('pull_request', False))
        self.labels = [label.get('name') for label in issue.get('labels', [])]
        self.repo = issue.get('repository').get('full_name')
        self.created_at = human_to_datetime(issue.get('created_at'))
        self.updated_at = human_to_datetime(issue.get('updated_at'))
        self.closed_at = human_to_datetime(issue.get('closed_at', None))
        self._comments = None
        self.comments_client = github['repos'][self.repo]['issues'][self.number]['comments']
        self.client = github['repos'][self.repo]['issues'][self.number]

    @property
    def comments(self):
        if self._comments is not None:
            return self._comments

        _comments = []
        for _comment in self.comments_client:
            _comments.append(Comment(self, **_comment))
        self._comments = _comments
        return self._comments

    def __unicode__(self):
        return ('{repo}#{number}'.format(**self.__dict__))

    def __str__(self):
        return self.__unicode__()


class AutoCloseIssues(object):
    default_closing_template = ('This {{ issue_type }} was automatically closed '
                                'due to lack of activity.')

    default_reminder_template = ('Hi {{ author }},\n\n'
                                 'This {{ issue_type }} will be automatically '
                                 'closed on {{ close_date }} due to lack of '
                                 'activity (comments or updates).\n\n'
                                 'You can keep this issue open by adding a '
                                 'comment or you can apply the {{ keep_open }} '
                                 'label to permanently disable auto-closing.')

    def __init__(self, **config):
        self.keep_open_label = config.get('keep_open_label', 'keep open')
        self.reminder_template = config.get('reminder_template',
                                            self.default_reminder_template)
        self.closing_template = config.get('closing_template',
                                           self.default_closing_template)
        self.notify_before = human_to_datetime(config.get('notify_after', '30 days') + ' ago')
        self.close_date = human_to_datetime('in ' + config.get('grace_period', '60 days'))
        self.labels = config.get('labels', [])
        self.repos = [repo.lower() for repo in config.get('repos', [])]
        self.skip_with_milestone = bool(config.get('skip_with_milestone', True))
        self.skip_pull_request = bool(config.get('skip_pull_request', False))
        self.skip_repos = [repo.lower() for repo in config.get('skip_repos', [])]
        self.skip_labels = config.get('skip_labels', [])
        self.skip_labels.append(self.keep_open_label)
        self.close_date_patterns = config.get('close_date_patterns', [
            (r'(.*)closed? on (.*) due to (.*)', r'\2')
        ])

        if config.get('since', None):
            self.issues_since = human_to_datetime(config.get('since'))
        else:
            self.issues_since = None

    def render_template(self, template, issue):
        context = {
            'author': issue.author,
            'issue_type': 'issue' if not issue.pull_request else 'pull request',
            'close_date': self.close_date.strftime('%a, %d %b %Y'),
            'keep_open': self.keep_open_label
        }
        return pystache.render(template, context)

    def get_close_date(self, message):
        for pattern in self.close_date_patterns:
            date_str = re.sub(pattern[0], pattern[1], message,
                              flags=re.IGNORECASE | re.DOTALL)
            try:
                date = maya.when(date_str)
                return date.datetime()
            except ValueError:
                pass
        return None

    def validate_config(self):
        context = {
            'author': 'octocat',
            'issue_type': 'issue',
            'close_date': self.close_date.strftime('%a, %d %b %Y'),
            'keep_open': self.keep_open_label
        }
        reminder = pystache.render(self.reminder_template, context)
        close_date = self.get_close_date(reminder)
        if not close_date or self.close_date.date() != close_date.date():
            raise ValueError("Could not parse back date from reminder template. "
                             "You should adjust the close_date_patterns config "
                             "option.")

    def get_issue_last_reminder(self, issue):
        bot_user = github.config.auth.username
        if not issue.comments:
            return None
        last_comment = issue.comments[-1]
        if (last_comment.author == bot_user and
                self.get_close_date(last_comment.body)):
            return last_comment
        else:
            return None

    def create_close_notification(self, issue):
        reminder = self.render_template(self.reminder_template, issue)
        issue.comments_client.post(body=reminder)

    def close_issue(self, issue):
        close_message = self.render_template(self.closing_template, issue)
        issue.comments_client.post(body=close_message)
        issue.client.patch(state='closed')

    def __call__(self):
        self.validate_config()
        filters = {
            'filter': 'all',
            'per_page': 100,
            'state': 'open',
        }
        if self.issues_since:
            filters['since'] = self.issues_since.isoformat()
        if self.labels:
            filters['labels'] = ','.join(self.labels)

        for _issue in github.issues[filters]:
            issue = Issue(**_issue)
            if self.repos and issue.repo.lower() not in self.repos:
                continue
            if issue.repo.lower() in self.skip_repos:
                continue
            if issue.milestone and self.skip_with_milestone:
                continue
            if self.skip_labels and set(issue.labels) & set(self.skip_labels):
                continue
            if self.skip_pull_request and issue.pull_request:
                continue

            if issue.updated_at < self.notify_before:
                last_reminder = self.get_issue_last_reminder(issue)
                close_date = None
                if last_reminder:
                    close_date = self.get_close_date(last_reminder.body)

                if close_date and close_date < maya.now().datetime():
                    print('Closing {issue} last updated at '
                          '{date}'.format(issue=issue, date=issue.updated_at))
                    self.close_issue(issue)
                elif not last_reminder or last_reminder.updated_at < self.notify_before:
                    print('Notifying {issue} last updated at '
                          '{date}'.format(issue=issue, date=issue.updated_at))
                    self.create_close_notification(issue)


def auto_close_issues(**kwargs):
    return AutoCloseIssues(**kwargs)()


def main():
    config = yaml.safe_load(open('broomer.yml'))

    github.config.auth = HTTPBasicAuth(config.get('bot', {}).get('github_user', ''),
                                       config.get('bot', {}).get('github_password', ''))

    auto_close_issues(**config.get('auto_close_issues', {}))

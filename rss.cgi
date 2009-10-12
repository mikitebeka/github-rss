#!/usr/bin/env python

import sqlite3
import json

LOAD_SQL = '''
SELECT *
FROM commits
ORDER BY time DESC
LIMIT 30
'''
def load_commits():
    db= sqlite3.connect("commits.db")
    cur = db.cursor()
    cur.execute(LOAD_SQL)
    for row in cur:
        yield row[0], row[1], json.loads(row[2])

CONTENT_TEMPLATE = '''
Added:
    %(added)s

Removed:
    %(removed)s

Modified:
    %(modified)s
'''

def content(added, removed, modified):
    env = {
        "added" : "\n    ".join((a["filename"] for a in added)),
        "removed" : "\n    ".join((r["filename"] for r in removed)),
    }

    diffs = []
    for change in modified:
        diffs.append("%(filename)s:\n%(diff)%s" % change)
    env["modified"] = "\n".join(diffs)

    return CONTENT_TEMPLATE % env


ENTRY_TEMPLATE = '''
<entry>
    <id>%(id)s</id>
    <link type="text/html" href="%(link)s" rel="alternate"/>
    <title>%(title)s</title>
    <updated>%(updated)s</updated>
    <content type="text">
        %(content)s
    </content>
    <author>
      <name>%(author)s</name>
    </author>
</entry>
'''
COMMIT_URL = "https://github.com/saucelabs/sauce/commit/%s" 

def commit2rss(id, time, commit):
    env = {
        "id" : id,
        "link" : COMMIT_URL % id,
        "title" : commit["message"],
        "author" : commit["committer"]["name"],
        "updated" : commit["committed_date"],
        "content" : content(commit["added"], commit["removed"],
                            commit["modified"])
    }

    return ENTRY_TEMPLATE % env

ATOM_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xml:lang="en-US" xmlns="http://www.w3.org/2005/Atom">
  <id>tag:github.com,2008:/feeds/saucelabs/commits/sauce/master</id>
  <link type="text/html" href="http://github.com/saucelabs/sauce/commits/master/" 
    rel="alternate"/>
  <link type="application/atom+xml" 
    href="http://github.com/feeds/saucelabs/commits/sauce/master" rel="self"/>
  <title>Recent Commits to sauce:master</title>
  <updated>%(time)s</updated>
  %(entries)s

</feed>
'''

if __name__ == "__main__":
    from time import strftime

    entries = []
    for id, time, commit in load_commits():
        entries.append(commit2rss(id, time, commit))

    env = {
        "time" : strftime("%Y-%m-%dT%H:%M:%S"),
        "entries" : "\n".join(entries),
    }

    print ATOM_TEMPLATE % env


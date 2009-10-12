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

ENTRY_TEMPLATE = '''
<entry>
    <id>%(id)s</id>
    <link type="text/html" href="%(link)s" rel="alternate"/>
    <title>%(title)s</title>
    <updated>%(updated)s</updated>
    <content type="html">
        %(content)s
    </content>
    <author>
      <name>%(author)s</name>
    </author>
</entry>
'''


if __name__ == "__main__":
    for commit in load_commits():
        print commit
        break


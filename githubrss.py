#!/usr/bin/env python

from urllib import urlopen, urlencode
import json
import sqlite3
from time import strptime, mktime, sleep, strftime
import config
from threading import Thread
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from cgi import escape
from os import fork
import socket
import httplib
import webbrowser
import logging as log

SCHEMA = '''
BEGIN;

CREATE TABLE commits (
    id CHAR[40] PRIMARY KEY,
    time FLOAT,
    data TEXT
);

CREATE INDEX commits_time ON commits(time);

END;
'''

def db_connect():
    return sqlite3.connect("commits.db")

def initialize_db():
    db = db_connect()
    try:
        cur = db.cursor()
        cur.executescript(SCHEMA)
        db.commit()
        db.close()
    except sqlite3.Error: # Assume it's there
        pass

def github(url):
    # FIXME: reload config?
    params = urlencode({
        "login" : config.login,
        "token" : config.token,
    })
    return json.load(urlopen(url, params))

BASE = "https://github.com/api/v2/json/commits/list/saucelabs/sauce/master"
COMMIT = "https://github.com/api/v2/json/commits/show/saucelabs/sauce/%s"

def parse_time(t):
    return mktime(strptime(t[:-6], "%Y-%m-%dT%H:%M:%S"))

def get_commits():
    result = github(BASE)
    for id in (commit["id"] for commit in result["commits"]):
        url = COMMIT % id 
        yield github(url)["commit"]

def store_new_commits(db, commits):
    cur = db.cursor()
    for commit in commits:
        id = commit["id"]
        time = parse_time(commit["committed_date"])
        text = json.dumps(commit)
        try:
            cur.execute("INSERT INTO commits VALUES (?, ?, ?)", (id, time, text))
        except sqlite3.IntegrityError:
            pass
    db.commit()
    db.close()

def fetcher_thread():
    db = db_connect()
    while 1:
        try:
            commits = list(get_commits())
            store_new_commits(db, commits)
        except IOError, e:
            log.error("%s" % e)

        raise SystemExit
        sleep(60)

LOAD_SQL = '''
SELECT *
FROM commits
ORDER BY time DESC
LIMIT 30
'''
def load_commits():
    db = db_connect()
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

def gen_diff(added, removed, modified):
    env = {
        "added" : "\n    ".join((a["filename"] for a in added)),
        "removed" : "\n    ".join((r["filename"] for r in removed)),
    }

    diffs = []
    for change in modified:
        diffs.append("%(filename)s:\n%(diff)s" % change)
    env["modified"] = "\n".join(diffs)

    return CONTENT_TEMPLATE % env

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
COMMIT_URL = "https://github.com/saucelabs/sauce/commit/%s" 

def commit2rss(id, time, commit):
    diff = gen_diff(commit["added"], commit["removed"], commit["modified"])
    env = {
        "id" : id,
        "link" : COMMIT_URL % id,
        "title" : commit["message"],
        "author" : commit["committer"]["name"],
        "updated" : commit["committed_date"],
        "content" : escape("<pre>%s</pre>" % diff)
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
def gen_atom():
    entries = []
    for id, time, commit in load_commits():
        entries.append(commit2rss(id, time, commit))

    env = {
        "time" : strftime("%Y-%m-%dT%H:%M:%S"),
        "entries" : "\n".join(entries),
    }

    return ATOM_TEMPLATE % env

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        data = gen_atom()
        self.send_response(httplib.OK)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", "%s" % len(data))
        self.end_headers()
        self.wfile.write(data)

def main(argv=None):
    import sys
    from optparse import OptionParser

    argv = argv or sys.argv

    parser = OptionParser("%prog ")
    parser.add_option("--no-fork", help="don't fork",
          dest="fork", action="store_false", default=1)

    opts, args = parser.parse_args(argv[1:])
    if args:
        parser.error("wrong number of arguments") # Will exit

    log.basicConfig(filename="githubrss.log",
        format="%(asctime)s:%(levelname)s:%(filename)s:%(lineno)s:%(message)s")
    log.getLogger().addHandler(log.StreamHandler())

    initialize_db()

    fetcher = Thread(target=fetcher_thread)
    fetcher.daemon = 1
    fetcher.start()

    port = 8421

    # fork to make program exit after opening the browser page
    if opts.fork:
        pid = fork()
        if pid:
            webbrowser.open("http://localhost:%s" % port)
    else:
        webbrowser.open("http://localhost:%s" % port)

    try:
        server = HTTPServer(("", port), RequestHandler)
        server.serve_forever()
    except socket.error:
        # Assume already running, we've opened the web page - enough
        pass

if __name__ == "__main__":
    main()

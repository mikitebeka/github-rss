#!/usr/bin/env python

from urllib import urlopen, urlencode
import json
import sqlite3
from time import strptime, mktime
import config

params = urlencode({
    "login" : config.login,
    "token" : config.token,
})

def github(url):
    print >> open("i.json", "w"), urlopen(url, params).read()
    return json.load(urlopen(url, params))

BASE = "https://github.com/api/v2/json/commits/list/saucelabs/sauce/master"
COMMIT = "https://github.com/api/v2/json/commits/show/saucelabs/sauce/%s"

def parse_time(t):
    return mktime(strptime(t[:-6], "%Y-%m-%dT%H:%M:%S"))

def get_commits():
    # result = github(BASE)
    result =  json.load(open("c.json"))
    for id in (commit["id"] for commit in result["commits"]):
        url = COMMIT % id 
        yield github(url)["commit"]

def main():
    db = sqlite3.connect("commits.db")
    cur = db.cursor()
    for commit in get_commits():
        id = commit["id"]
        time = parse_time(commit["committed_date"])
        text = json.dumps(commit)
        try:
            cur.execute("INSERT INTO commits VALUES (?, ?, ?)", (id, time, text))
        except sqlite3.IntegrityError:
            pass
    db.commit()
    db.close()

if __name__ == "__main__":
    main()

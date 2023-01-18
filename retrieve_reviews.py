#!/usr/bin/python3
import os
import sys
import requests
import re
import json
import urllib
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s")
review_select_condition = "(status:merged OR status:abandoned) AND after:{} AND before:{}"
url_format_str = "{}/changes/?q={}&n={}"
max_returned_results = 10000
proxy = "http://127.0.0.1:1087"
date_delta = 5

projects = [
    {
        "name": "QT",
        "time-start": "2011-05-01",
        "time-end": "2012-05-31",
        "url": "https://codereview.qt-project.org"
    },
    {
        "name": "LibreOffice",
        "time-start": "2012-03-01",
        "time-end": "2014-06-30",
        "url": "https://gerrit.libreoffice.org"
    },
    {
        "name": "OpenStack",
        "time-start": "2011-07-01",
        "time-end": "2012-05-31",
        "url": "https://review.opendev.org"
    },
    {
        "name": "Android",
        "time-start": "2008-10-01",
        "time-end": "2012-01-31",
        "url": "https://android-review.googlesource.com"
    }
]
def download(url):
    if proxy is not None:
        return requests.get(url, proxies={ 'http': proxy, 'https': proxy })
    else:
        return requests.get(url)

if __name__ == "__main__":
    for project in projects:
        logging.info('Start process {}...'.format(project["name"]))
        start_date = datetime.date.fromisoformat(project["time-start"])
        end_date = datetime.date.fromisoformat(project["time-end"])
        review_list = []

        while start_date < end_date:
            date_from = start_date
            date_to = date_from + datetime.timedelta(days=date_delta)
            if date_to > end_date:
                date_to = end_date
            logging.info('Fetch from {} to {}...'.format(date_from.isoformat(), date_to.isoformat()))
            url = "{}/changes/?q={}&n={}&o=CURRENT_REVISION&o=CURRENT_FILES&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS&o=CURRENT_COMMIT".format(project["url"], 
                urllib.parse.quote(review_select_condition.format(date_from.isoformat(), date_to.isoformat())),
                max_returned_results
            )

            logging.info('Fetch URL: {}'.format(url))
            r = download(url)
            reviews_obj = json.loads(r.text[5:])
            logging.info('{} reviews fetched.'.format(len(reviews_obj)))
            
            for review in reviews_obj:
                change_id = review["id"]
                try:
                    current_revision_id = review["current_revision"]
                    
                    review_list.append({
                        "id": review["id"],
                        "uploaded-time": review["created"],
                        "reviewers": [ { "id": x["_account_id"], "name": x["name"] } for x in review["reviewers"]["REVIEWER"] ],
                        "textual-content": review["revisions"][current_revision_id]["commit"]["message"],
                        "changed-files": list(review["revisions"][current_revision_id]["files"].keys())
                    })
                    logging.debug('Review {} processed.'.format(review["_number"]))
                except Exception as e:
                    logging.error('Error occured: {}'.format(str(e)))
            start_date = date_to

        logging.info('{} reviews in total belonging to {}'.format(len(review_list), project["name"]))
        f = open(project["name"] + '.json', 'w')
        f.write(json.dumps(review_list))
        logging.info('Written to {}.\n'.format(project["name"] + '.json'))
        f.close()
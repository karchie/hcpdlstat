# Copyright (c) 2013 Washington University School of Medicine
# Author: Kevin A. Archie <karchie@wustl.edu>

import argparse, os
import ConfigParser
from collections import Counter
import pymysql

_status_types = ['completed', 'cancelled', 'error']

# We count a few file types by pattern matching names.
_counted_status_file_types = [
    ('unproc_completed', 'completed', '%_unproc.zip'),
    ('preproc_completed', 'completed', '%_preproc.zip')]

def get_stats_status(db, stats, date, status):
    cur = db.cursor()
    try:
        cur.execute("select count(session_id) from aspera_stats_collector.fasp_sessions where date(created_at)='{}' and status='{}'".format(date, status))
        stats[status+'_sessions']=int(cur.fetchall()[0][0])

        cur.execute("select count(distinct(cookie)) from aspera_stats_collector.fasp_sessions where date(created_at)='{}' and status='{}'".format(date, status))
        stats[status+'_users']=int(cur.fetchall()[0][0])

        cur.execute("select sum(bytes_written) from aspera_stats_collector.fasp_files where date(created_at)='{}' and status='{}'".format(date, status))
        r = cur.fetchall()[0][0]
        stats[status+'_bytes']=int(r) if r else 0
        return stats
    finally:
        cur.close()

def get_counted_file_stats(db, stats, date):
    cur = db.cursor()
    try:
        for (k,status,pattern) in _counted_status_file_types:
            cur.execute("select count(id) from aspera_stats_collector.fasp_files where date(created_at)='{}' and status='{}' and file_fullpath like '{}'".format(date, status, pattern))
            stats[k]=int(cur.fetchall()[0][0])
        return stats
    finally:
        cur.close()

def get_stats(db, date, stats=None):
    if not stats:
        stats = {'date':date}
    for status in _status_types:
        get_stats_status(db, stats, date, status)
    get_counted_file_stats(db, stats, date)
    return stats

def array_stats(s):
    return [str(s[f]) if f else ''
                for f in ['date',
                          'completed_sessions',
                          'completed_users',
                          'completed_bytes',
                          None,
                          'cancelled_sessions',
                          'cancelled_users',
                          None,
                          'error_sessions',
                          'error_users']]
def main():
    config = ConfigParser.ConfigParser()
    config.read(['site.cfg', os.path.expanduser('~/.hcpdlstat.cfg')])
    get_config = lambda k: config.get('statscollector',k)

    host = get_config('mysql.host')
    port = int(get_config('mysql.port'))
    user = get_config('mysql.user')
    passwd = get_config('mysql.password')

    argparser = argparse.ArgumentParser(description='Extract statistics from Aspera stats collector database.')
    argparser.add_argument('-d', '--date',
                           help='specify the log date (yyyy-mm-dd)')
    argparser.add_argument('-c', '--csv',
                           help='produce CSV-formatted output',
                           action='store_true')
    args = argparser.parse_args()

    db = pymysql.connect(host=host,port=port,user=user,passwd=passwd)
    try:
        stats = get_stats(db, args.date)
        if args.csv:
            print ','.join(array_stats(stats))
        else:
            print stats
    finally:
        db.close()

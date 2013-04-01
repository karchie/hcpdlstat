#!/usr/bin/python

import argparse, os
import ConfigParser
from collections import Counter
import pymysql

def get_stats_status(db, stats, date, status):
    cur = db.cursor()
    try:
        cur.execute("select count(session_id) from aspera_stats_collector.fasp_sessions where date(created_at)='{0}' and status='{1}'".format(date, status))
        stats[status+'_sessions']=int(cur.fetchall()[0][0])

        cur.execute("select count(distinct(cookie)) from aspera_stats_collector.fasp_sessions where date(created_at)='{0}' and status='{1}'".format(date, status))
        stats[status+'_users']=int(cur.fetchall()[0][0])

        cur.execute("select sum(bytes_written) from aspera_stats_collector.fasp_files where date(created_at)='{0}' and status='{1}'".format(date, status))
        r = cur.fetchall()[0][0]
        stats[status+'_bytes']=int(r) if r else 0
    finally:
        cur.close()
    return stats


def get_stats(db, date, stats):
    for status in ['completed', 'cancelled', 'error']:
        get_stats_status(db, stats, date, status)
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
        stats = get_stats(db, args.date, {'date': args.date})
        if args.csv:
            print ','.join(array_stats(stats))
        else:
            print stats
    finally:
        db.close()


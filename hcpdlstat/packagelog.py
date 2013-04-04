# Parse the XNAT package downloads log (package-downloads.log)
# Copyright (c) 2013 Washington University School of Medicine
# Author: Kevin A. Archie <karchie@wustl.edu>

import argparse, datetime, fileinput, os, re, sys, ConfigParser
from collections import defaultdict, Counter
from pyparsing import Suppress, Word, alphanums, delimitedList, nums, printables, ParseException
from bundles import g1, g5, g20, counted_resources

def date():
    year = Word(nums, exact=4)
    month_or_day = Word(nums, exact=2)
    date = year + Suppress('-') + month_or_day + Suppress('-') +  month_or_day
    return date.setResultsName('date')

def time():
    chunk = Word(nums, exact=2)
    ms = Word(nums)
    time = chunk + Suppress(':') + chunk + Suppress(':') + chunk + Suppress(',') + ms
    return time.setResultsName('time')

def login():
    login = Word(alphanums + '_')
    return login.setResultsName('login')

def packages():
    pkgs = delimitedList(Word(alphanums + '_'), ',')
    return pkgs.setResultsName('packages')

def subject():
    return Word(alphanums)

def subjects():
    subjects = Suppress('[') + delimitedList(subject(), ',') + Suppress(']')
    return subjects.setResultsName('subjects')

def bytes_requested():
    br = Suppress('(') + Word(nums) + Suppress('bytes)')
    return br.setResultsName('bytes_requested')

def package_line():
    return ( date() + time() + login() + 'downloading' +
             packages() + 'x' + subjects() +
             bytes_requested() )

def filename():
    return Word(printables).setResultsName('filename')

def project():
    return Word(alphanums + '_').setResultsName('project')

def resource():
    return Word(alphanums + '_').setResultsName('resource')

def resource_line():
    return ( date() + time() + login() + 'downloading' +
             filename() + 'from' + 'project' + project() + ',' +
             'resource' + resource() + bytes_requested())
             
def logline():
    return package_line() | resource_line()
                

def handle_line_packages(stats, parse_results):
    subjects = set(parse_results['subjects'])
    packages = parse_results['packages']
    if g1 == subjects:
        group = 'g1'
    elif g5 == subjects:
        group = 'g5'
    elif g20 == subjects:
        group = 'g20'
    else:
        group = None
    if group:
        stats[group] = stats[group] + 1
        stats[group + '_files'] = stats[group + '_files'] + len(packages)
    for package in packages:
        for type in ['unproc', 'preproc']:
            if re.search(type, package):
                stats[type] = stats[type] + len(subjects)
    stats['files'] = stats['files'] + len(subjects) * len(packages)
    stats['bytes'] = stats['bytes'] + int(parse_results['bytes_requested'][0])

def handle_line_resource(stats, parse_results):
    stats['files'] = stats['files'] + 1
    p = parse_results['project']
    r = parse_results['resource']
    f = parse_results['filename']
    stats['resources'][p][r].update([f])
    stats['bytes'] = stats['bytes'] + int(parse_results['bytes_requested'][0])
    
def handle_line(stats, parse_results):
    if 'packages' in parse_results:
        handle_line_packages(stats, parse_results)
    else:
        handle_line_resource(stats, parse_results)

def handle_lines(lines, stats):
    parser = logline()
    for line in lines:
        try:
            handle_line(stats, parser.parseString(line))
        except ParseException as e:
            print e.markInputline()
            raise
    for k,v in counted_resources.items():
        stats[k] = reduce(lambda e,k: e[k], v, stats['resources'])

def init_stats():
    s = {'date':'',
         'g1': 0, 'g5': 0, 'g20': 0,
         'g1_files': 0, 'g5_files': 0, 'g20_files': 0,
         'files': 0, 'bytes': 0,
         'resources': defaultdict(lambda: defaultdict(Counter)),
         'unproc': 0, 'preproc': 0}
    for k in counted_resources:
        s[k] = 0
    return s

def display_stats(stats):
    print stats['files'], 'files,', stats['bytes'], 'bytes'
    print stats['unproc'], 'unprocessed,', stats['preproc'], 'preprocessed'
    print 'Group of  1:', stats['g1'], 'request =', stats['g1_files'], 'files'
    print 'Group of  5:', stats['g5'], 'request =', stats['g5_files'], 'files'
    print 'Group of 20:', stats['g20'], 'request =', stats['g20_files'], 'files'
    if stats['resources']:
        print 'Resources:'
    for project,rmap in stats['resources'].iteritems():
        for resource, counter in rmap.iteritems():
            for f, count in counter.iteritems():
                print ' ', project, resource, f, count

def array_stats(stats):
    return [str(stats[f]) if f else ''
            for f in ['date',
                      'g1', 'g1_files',
                      'g5', 'g5_files',
                      'g20', 'g20_files',
                      None,
                      'preproc', None,
                      'unproc', None]]
    
def build_log_path(stats, dir, name, s):
    """Builds the full pathname of a log file from the log directory,
    the log basename, and the date (datetime.date, 'today', 'yesterday',
    or 'yyyy-mm-dd')."""
    if 'today' == s:
        stats['date'] = datetime.date.today()
        return os.path.join(dir, name)
    elif 'yesterday' == s:
        date = datetime.date.today()-datetime.timedelta(days=1)
    elif isinstance(s, datetime.date):
        date = s
    else:
        date = datetime.datetime.strptime(s, '%Y-%m-%d').date()
    stats['date'] = date
    return os.path.join(dir, name + '.' + date.isoformat())

def get_stats(logdir, logname, date):
    stats = init_stats()
    logfile = build_log_path(stats, logdir, logname, date)
    try:
        with open(logfile) as logf:
            handle_lines(logf.readlines(), stats)
    except IOError as e:
        # no logfile probably just means no downloads for that date;
        # that's the initial value of the stats dict anyway.
        if os.path.exists(logfile):
            raise e         # file exists but something went wrong
        else:
            sys.stderr.write('No logfile for {} - assuming zero downloads\n'.format(date))
    return stats



def main():
    config = ConfigParser.ConfigParser()
    config.read(['site.cfg', os.path.expanduser('~/.hcpdlstat.cfg')])
    get_config = lambda k: config.get('packagelog',k)
    
    argparser = argparse.ArgumentParser(description='Extract statistics from XNAT package request log.')
    argparser.add_argument('-d', '--date',
                           help='specify the log date (today, yesterday, or yyyy-mm-dd)',
                           metavar='DATE',
                           type=lambda s: build_log_path(stats,
                                                         get_config('logdir'),
                                                         get_config('logname'),
                                                         s),
                           dest='logfile')
    argparser.add_argument('-c', '--csv',
                           help='produce CSV-formatted output',
                           action='store_true')
    argparser.add_argument('logfiles', nargs='*',
                           metavar='[LOG-FILE-PATH ...]')
    args = argparser.parse_args()
    if args.logfile:
        with open(args.logfile) as f:
            lines = f.readlines()
    else:
        lines = fileinput.input(files=args.logfiles)

    stats = init_stats()
    handle_lines(lines, stats)
    if args.csv:
        print ','.join(array_stats(stats))
    else:
        display_stats(stats)

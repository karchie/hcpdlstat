#!/usr/bin/python
# Parse the XNAT package downloads log (package-downloads.log)
# Copyright (c) 2013 Washington University School of Medicine
# Author: Kevin A. Archie <karchie@wustl.edu>

import argparse, datetime, fileinput, os, re, ConfigParser
from collections import defaultdict, Counter
from pyparsing import Suppress, Word, alphanums, delimitedList, nums, printables, ParseException
from bundles import g1, g5, g20

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
                

def handle_line_packages(state, parse_results):
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
        state[group] = state[group] + 1
        state[group + '_files'] = state[group + '_files'] + len(packages)
    for package in packages:
        for type in ['unproc', 'preproc']:
            if re.search(type, package):
                state[type] = state[type] + len(subjects)
    state['files'] = state['files'] + len(subjects) * len(packages)
    state['bytes'] = state['bytes'] + int(parse_results['bytes_requested'][0])

def handle_line_resource(state, parse_results):
    state['files'] = state['files'] + 1
    p = parse_results['project']
    r = parse_results['resource']
    f = parse_results['filename']
    state['resources'][p][r].update([f])
    state['bytes'] = state['bytes'] + int(parse_results['bytes_requested'][0])
    
def handle_line(state, parse_results):
    if 'packages' in parse_results:
        handle_line_packages(state, parse_results)
    else:
        handle_line_resource(state, parse_results)

def handle_lines(lines, state):
    parser = logline()
    for line in lines:
        try:
            handle_line(state, parser.parseString(line))
        except ParseException as e:
            print e.markInputline()
            raise

def init_state():
    return {'date':'',
            'g1': 0, 'g5': 0, 'g20': 0,
            'g1_files': 0, 'g5_files': 0, 'g20_files': 0,
            'files': 0, 'bytes': 0,
            'resources': defaultdict(lambda: defaultdict(Counter)),
            'unproc': 0, 'preproc': 0}

def display_state(state):
    print state['files'], 'files,', state['bytes'], 'bytes'
    print state['unproc'], 'unprocessed,', state['preproc'], 'preprocessed'
    print 'Group of  1:', state['g1'], 'request =', state['g1_files'], 'files'
    print 'Group of  5:', state['g5'], 'request =', state['g5_files'], 'files'
    print 'Group of 20:', state['g20'], 'request =', state['g20_files'], 'files'
    if state['resources']:
        print 'Resources:'
    for project,rmap in state['resources'].iteritems():
        for resource, counter in rmap.iteritems():
            for f, count in counter.iteritems():
                print ' ', project, resource, f, count

def array_state(state):
    return [str(state[f]) if f else ''
            for f in ['date',
                      'g1', 'g1_files',
                      'g5', 'g5_files',
                      'g20', 'g20_files',
                      None,
                      'preproc', None,
                      'unproc', None]]
    
def build_log_path(state, dir, name, s):
    """Builds the full pathname of a log file from the log directory,
    the log basename, and the date (today, yesterday, or yyyy-mm-dd)."""
    if 'today' == s:
        state['date'] = datetime.date.today().isoformat()
        return os.path.join(dir, name)
    elif 'yesterday' == s:
        date = (datetime.date.today()-datetime.timedelta(days=1)).isoformat()
        state['date'] = date
        return os.path.join(dir, name + '.' + date)
    else:
        state['date'] = s
        return os.path.join(dir, name + '.' + s)

def main():
    config = ConfigParser.ConfigParser()
    config.read(['site.cfg', os.path.expanduser('~/.hcpdlstat.cfg')])
    get_config = lambda k: config.get('parsepkglog',k)
    
    argparser = argparse.ArgumentParser(description='Extract statistics from XNAT package request log.')
    argparser.add_argument('-d', '--date',
                           help='specify the log date (today, yesterday, or yyyy-mm-dd)',
                           metavar='DATE',
                           type=lambda s: build_log_path(state,
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

    state = init_state()
    handle_lines(lines, state)
    if args.csv:
        print ','.join(array_state(state))
    else:
        display_state(state)

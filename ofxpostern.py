#!/usr/bin/env python3

'''
Fingerprint an OFX server.
'''

# Options Parsing
# ofx-postern <url> [fid] [org]
#             -c clear cache
#
# ofx-postern
# Enter name of financial institution
# > Cit
# 1) Citi Bank
# 2) Citi Bank Financial
# Select a financial institution:
# > 2

# Output
# 1) Connection Methods
#    * DirectConnect (OFX)
#    * Express Web Connect (Intuit API)
#    * Web Connect (File download)
# 2) Connection Info
#    * URL
#    * SSL Certificate expiration date
# 3) Capabilities
#    * Checking
#    * Savings
#    * Bill Pay
#    * etc...
# 4) Fingerprint
#    * Service Provider?
#    * HTTP Server
#    * Application Framework
#    * OFX Server
#      - Company
#      - Product
#      - Version
# 5) Tests
#    * Information Disclosure
#    * Zombie Server
#    * Null values returned
#    * Long lived session keys
#    * XSS
#    * TLS

# Download FI list
# - cache it
# - create .postern in homedir

# Search
# - read FI data file
# - pull capabilities from FI file

# Send Requests
# - cache the results
# - determine TLS issues

# Capabilities
# - pull from PROFILE request
# - else pull from fidata

# Fingerprint
# - review responses
# - print results

# Test
# - review responses
# - print results

import argparse
import json
import os
import sys
import time

import testofx

#
# Defines
#

PROGRAM_DESCRIPTION = 'Fingerprint an OFX server.'
PROGRAM_NAME = 'ofxpostern'
VERSION = '0.0.1'

DATA_DIR = '{}/.{}'.format(os.environ['HOME'], PROGRAM_NAME)
FIS_DIR = '{}/{}'.format(DATA_DIR, 'fi')
FI_DIR_FMT = '{}/{}'.format(FIS_DIR, '{}-{}-{}')

STR_HEADERS = 'headers'
STR_BODY    = 'body'

#
# Globals
#

debug = True

fi_dir = ''

req_results = {}

#
# Helper Functions
#

def init(server):
    '''
    Initialize environment
    '''

    global fi_dir

    # Convert URL into usable filename
    url_fname = server.ofxurl.partition('/')[2][1:].replace('/','_').replace('&','+')
    fi_dir = FI_DIR_FMT.format(url_fname, server.fid, server.org)

    # Create directory to store cached data
    os.makedirs(DATA_DIR, mode=0o770, exist_ok=True)
    os.makedirs(FIS_DIR, mode=0o770, exist_ok=True)
    os.makedirs(fi_dir, mode=0o770, exist_ok=True)


def print_debug(msg):
    if debug: print('DEBUG: {}'.format(msg))


def print_header(msg, lvl):
    '''
    Print a header with underline on 2nd line

    Similar to <H1>, <H2>
    '''
    under_char = ''

    if lvl == 1: under_char = '#'
    elif lvl == 2: under_char = '='
    elif lvl == 3: under_char = '-'
    else: raise ValueError('Unknown lvl: {}'.format(lvl))

    print(msg)
    print(under_char * len(msg))


def print_kv_list(kv_list):
    '''
    Print key:value list with pretty formatting

    kv_list: list[tuples]
    '''

    k_width = 0
    for k, v in kv_list:
        if len(k) > k_width:
            k_width = len(k)

    for k, v in kv_list:
        print('{:{}} {}'.format(k+':', k_width+1, v))

#
# Core Logic
#

def send_profile_req(server):
    '''
    Send profile request to the OFX server.
    '''

    req_name = testofx.REQ_NAME_OFX_PROFILE
    otc = testofx.OFXTestClient(output=debug)
    res = otc.send_req(req_name, server)

    # Store persistently for debugging
    res_name_base = req_name.replace('/', '+').replace(' ', '_')
    with open('{}/{}-{}'.format(fi_dir, res_name_base, STR_HEADERS), 'w') as fd:
        fd.write(json.dumps(dict(res.headers)))
    with open('{}/{}-{}'.format(fi_dir, res_name_base, STR_BODY), 'w') as fd:
        fd.write(res.text)

    # Store result for analysis
    req_results[req_name] = res


def report_cli_fi(profrs):
    '''
    Print Financial Institution information
    '''

    print_header('Financial Institution', 2)
    print()

    fi_list = []
    output = (
            ('FINAME', 'Name'),
            ('ADDR1', 'Address'),
            ('ADDR2', ''),
            ('ADDR3', ''),
            )

    for tup in output:
        try:
            val = profrs.profile[tup[0]]
            fi_list.append((tup[1], val))
        except KeyError: pass

    city = ''
    state = ''
    postalcode = ''

    try:
        city = profrs.profile['CITY']
        state = profrs.profile['STATE']
        postalcode = profrs.profile['POSTALCODE']
    except KeyError: pass

    fi_list.append(('', '{}, {} {}'.format(city, state, postalcode)))

    country = ''

    try:
        country = profrs.profile['COUNTRY']
    except KeyError: pass

    fi_list.append(('', country))

    print_kv_list(fi_list)

    print()


def report_cli_server(profrs):
    '''
    Print server information
    '''
    print_header('OFX Server', 2)
    print()

    fi_list = []

    try:
        val = profrs.signon['FID']
        fi_list.append(('FID', val))
    except KeyError: pass

    try:
        val = profrs.signon['ORG']
        fi_list.append(('ORG', val))
    except KeyError: pass

    try:
        val = profrs.profile['OFXURL']
        fi_list.append(('URL', val))
    except KeyError: pass

    print_kv_list(fi_list)

    print()


def report_cli(profrs):
    '''
    Print human readable report of all results to stdout
    '''
    report_cli_fi(profrs)
    report_cli_server(profrs)


def main():

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION)
    parser.add_argument('url',
            help='URL of OFX server to test')
    parser.add_argument('-f', '--fid',
            help='Financial ID of Institution',
            required=False)
    parser.add_argument('-o', '--org',
            help='Organization within the Institution',
            required=False)
    args = parser.parse_args()

    print_debug(args)

    # TODO: validate input
    server = testofx.OFXServerInstance(args.url, args.fid, args.org)

    # Initialize Persistent Cache
    init(server)

    # Display work in progress
    print('{}: version {}'.format(parser.prog, VERSION))
    print()
    print('Start: {}'.format(time.asctime()))
    print('  Sending <PROFRQ>')
    send_profile_req(server)
    print('End:   {}'.format(time.asctime()))
    print()

    # Analyze results
    profrs = testofx.OFXFile(req_results[testofx.REQ_NAME_OFX_PROFILE].text)

    # Print Report
    report_cli(profrs)

if __name__ == '__main__':
    main()

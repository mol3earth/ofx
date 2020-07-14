#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:31:59 2020

@author: mark
"""

import bs4 
from datetime import datetime, timedelta, timezone
import ofxtools
import keyring # note, on WSL keyrings.alt is a dependency, but does not need importing
from matplotlib import pyplot, dates as mp_dates, ticker
import numpy
import sys, getopt
import os

def findConfig():
    path = os.getcwd()
    if path[:6] == '/home/':
        file_path = '/'.join(path.split('/')[:3]) + \
            '/.config/ofxtools/ofxget.cfg'
        if os.path.exists(file_path):
            print('Trying found config file: ' + file_path)
            configFile = file_path
        else: 
            print('Found no config file. Exiting')
            sys.exit()
    return configFile

def stmtFromFile(file):
    """
    opens an ofx formatted xml file and converts to beautiful soup object

    Parameters
    ----------
    file : str, optional
        DESCRIPTION. filename and path
        The default is filePath+fileName.

    Returns
    -------
    stmt : beautiful soup object
        DESCRIPTION. 

    """
    try: 
        with open(file,'r') as stmts:
            stmt = bs4.BeautifulSoup(stmts,'xml')
    except FileNotFoundError as ex:
        raise ex
    return stmt

def getConfigs(config):
    """
    opens an ofx config file and parses for account information. returns a 
    dict with keys of the account nicknames and value is another dict with 
    account params

    Parameters
    ----------
    config : str, optional
        DESCRIPTION. The full path to the ofx config file.
        The default is ofxConfigFile.

    Returns
    -------
    configs : dict
        DESCRIPTION. dict of all account configs in the ofx config file.

    """
    try: 
        with open(config) as f:
            figFile = f.read()
    except FileNotFoundError as ex:
        print('Config file not found.')
        raise ex 
    configs = {}
    acctConfig = {}
    for line in figFile.splitlines():
        if line == '':
            configs[this] = acctConfig
        elif line[0] == '[':
            this = line[1:-1]
            acctConfig = {}
        else:
            keyval = line.split(' = ')
            acctConfig[keyval[0]] = keyval[1]
    configs[this] = acctConfig
    return configs

def loadConfig(config):
    """
    creates a ofxtool client from given config

    Parameters
    ----------
    config : dict
        DESCRIPTION. dict of configuration information. 
            keys required:
                url, user, clientuid, version, appid, appver
            optional, though required by some organizations
                bankid, fid, org

    Returns
    -------
    client : ofx client object
        DESCRIPTION. See ofxget

    """
    client = ofxtools.Client.OFXClient(
        config['url'],
        userid=config['user'], 
        clientuid=config['clientuid'], 
        version=int(config['version']), 
        appid=config['appid'], 
        appver=config['appver']
    )
    if 'bankid' in config.keys():
        client.bankid = config['bankid']
        client.fid = config['fid'],
        client.org = config['org'],
    return client

def ofxDT(dt):
    """
    converts a offset-naive datetime object into a ofxtool UTC datetime object

    Parameters
    ----------
    dt : datetime object
        DESCRIPTION.

    Returns
    -------
    ofxtools UTC calibrated datetime object
        DESCRIPTION.

    """
    return datetime(dt.year, dt.month, dt.day, tzinfo=ofxtools.utils.UTC)

def getPassword(institution):
    try:
        return keyring.get_password('ofxtools', institution) 
    except:
        print('could not load password via: keyring.get_password("ofxtools", <institution> )')
        print('did you properly configure your password with keyring?')
        raise

def stmtFromOFX(org, start, end, config_file):
    """
    requests a statement from a given organization, and start and end dates

    Parameters
    ----------
    org : str
        DESCRIPTION. an organization in your ofxtools config file
    start : datetime object
        DESCRIPTION. start date of account statement
    end : datetime object
        DESCRIPTION. end date of account statement

    Returns
    -------
    stmt : beautifulsoup object of ofx xml
        DESCRIPTION. contains a list of transactions, and balance of account

    """
    config = getConfigs(config_file)[org]
    client = loadConfig(config)
    dtstart = ofxDT(start)
    dtend = ofxDT(end)
    if 'creditcard' in config.keys():
        ccs = ofxtools.Client.CcStmtRq(
                config['creditcard'], 
                dtend=dtend, 
                dtstart=dtstart
        )
    else:
        ccs = ofxtools.Client.StmtRq(
                config['checking'], 
                accttype = 'CHECKING',
                dtend=dtend,
                dtstart=dtstart
        )
    password = getPassword(org)
    r = client.request_statements( 
        password,
        ccs
    )
    bt = r.read()
    stmt = bs4.BeautifulSoup(bt.decode('utf-8'),'xml')
    return stmt
    

def pastSaturday(dt):
    """
    finds the most recent saturday from a given date.

    Parameters
    ----------
    dt : datetime object
        DESCRIPTION. 

    Returns
    -------
    datetime object
        DESCRIPTION. datetime object of the previous saturday from given date

    """
    fromSun = dt.isoweekday() % 7 
    return dt - timedelta( fromSun + 1)

def firstOfMonth(dt):
    """
    Returns a datetime object of the first of the month for the given dates 
    month.

    Parameters
    ----------
    dt : datetime object
        DESCRIPTION. 

    Returns
    -------
    datetime object
        DESCRIPTION. 

    """
    return dt - timedelta( dt.day -1 )

def dtNowUtc():
    """
    returns a datetime object 

    Returns
    -------
    dtNow : TYPE
        DESCRIPTION.

    """
    dtNow = datetime.now(timezone.utc)
    dtNow = dtNow.astimezone()
    return dtNow

def makePositive(number):
    """
    makes transactions positive numbers if negative and 0 if positive. 
    this makes spending increase, and ignores payments of credit accounts

    Parameters
    ----------
    number : int
        DESCRIPTION.

    Returns
    -------
    number : float
        DESCRIPTION.

    """
    number = float(number)
    if number < 0:
        number = number*-1
    else:
        number = 0
    return number

def addBuffer(string, length = 9):
    buffSize = (length - len(string))/2
    before = ' '*int(buffSize)
    after = ' '*int(buffSize)
    buffStr = before + string + after
    return buffStr[:length-1]

def makeKeys(startDate, increment='daily'):
    """
    initializes a dict with keys of dates, and values of amnts, inst, total 
    
    WARNING: monthly does not work accurately at the moment. 
    
    Parameters
    ----------
    sort : str, one of 'weekly', 'monthly'
        DESCRIPTION. dates will be daily, weekly, or monthly 
    startDate : datetime object
        DESCRIPTION. 

    Returns
    -------
    allTrans : dict
        DESCRIPTION. a dict of dates as keys and a dict of keys of amnts, 
        inst, total

    """
    allTrans = {}
    n = (dtNowUtc() - startDate).days
    increment = {
        'daily'  :  1,
        'weekly' :  7,
        'monthly': 30
        }[increment]
    for d in range(0,n,increment):
        allTrans[
            (startDate + timedelta(d)).strftime('%Y%m%d')
            ] = {
                'amnts': [],
                 'inst' : [],
                 'total': 0.00
                 }
    return allTrans

def getTransactions(stmt, **kwargs):
    """
    parses a beautiful soup object of ofx xml transations 

    Parameters
    ----------
    stmt : beautiful soup object
        DESCRIPTION. an ofx formated xml document as a beautiful soup object
    startDate : datetime object, optional
        DESCRIPTION. The default is datetime(1800,1,1).
    sort : str, optional
        DESCRIPTION. The default is 'daily'. Can be 'weekly' or 'monthly'

    Returns
    -------
    allTrans : dict
        DESCRIPTION. dict of all transactions in the stmt with keys of dates

    """
    startDate = kwargs.get('startDate', datetime(2000,1,1))
    increment = kwargs.get('increment', 'daily')
    allTrans = makeKeys(startDate, increment)
    total = 0.0
    for trans in stmt.findAll('STMTTRN'):
        date = trans.DTPOSTED.text[:8]
        time = trans.DTPOSTED.text[8:14]
        dt = datetime(
            int(date[0:4]), 
            int(date[4:6]), 
            int(date[6:8]),
            int(time[0:2]),
            int(time[2:4]),
            int(time[4:]),
            tzinfo=ofxtools.utils.UTC
        )
        if  dt.astimezone() > startDate:                
            amnt = makePositive( trans.TRNAMT.text )
            comp = trans.NAME.text
            #print(' | '.join([date,addBuffer(str(amnt)),comp]))
            allTrans[date]['amnts'].append(amnt)
            allTrans[date]['inst'].append(comp)
            allTrans[date]['total']+=amnt
            total+=amnt
    allTrans['total'] = total
    return allTrans

def printTrans(allTrans):
    """
    loops over the transactions in allTrans and prints them

    Parameters
    ----------
    allTrans : dict
        DESCRIPTION. dict of transactions 

    Returns
    -------
    None.

    """
    print('-'*43)
    for date in allTrans.keys():
        if date != 'total':
            print(date)
            for i in range(len(allTrans[date]['amnts'])):
                print('\t%s - %s' % (
                    format( allTrans[date]['amnts'][i], ' >8.2f'),
                    allTrans[date]['inst'][i]
                    )
                )
            print('\t%s - TOTAL' % ( 
                format( allTrans[date]['total'], ' >8.2f')
                ) 
            )
    print('\t--------')
    print('Total:\t%s' % (
            format( allTrans['total'], ' >8.2f')
            )
    )
    print('-'*43)

def plotTrend(allTrans, **kwargs):
    """
    plots daily spending against weekly goal for a given transaction statement
    saves the figure if a filename is given.

    Parameters
    ----------
    allTrans : dict
        DESCRIPTION. dict of transactions 
    weeklygoal : float, optional
        DESCRIPTION. Weekly spending goal. The default is 500.00.
    saveFile : str, optional
        DESCRIPTION. filepath for location and name of file if want it saved

    Returns
    -------
    None.

    """
    weeklygoal = kwargs.get('weeklygoal',500.00)
    save_file = kwargs.get('save_file')
        
    fig = pyplot.figure()
    # set xtick angle relative to density of dates
    pyplot.xticks( 
        rotation=int(max(10,len(allTrans)/5*10))
        )
    ax = fig.gca()#add_subplot(111,label="1")
    dates = []
    money = []
    goals = []
    runningtotal=0.00
    daily = weeklygoal/7
    goal = 0.0
    for date in allTrans.keys():
        if date != 'total':
            #dates.append("-".join([date[0:4],date[4:6],date[6:8]]))
            dates.append( datetime.strptime(date,"%Y%m%d") )
            runningtotal+=allTrans[date]['total']
            money.append(runningtotal)
            goal += daily
            goals.append(goal)
    formatter = ticker.FormatStrFormatter('$%1.2f')
    ax.yaxis.set_major_formatter(formatter) 
    ax.xaxis.set_major_formatter(mp_dates.DateFormatter('%m/%d/%Y'))
    ax.xaxis.set_major_locator(mp_dates.DayLocator())
    ax.plot_date(dates, money, 'bo-')
    ax.plot_date(dates, goals, 'k*--')
    idx = min(len(dates)-2,1)
    ax.text( dates[idx], goals[idx], ' $%.2f/week Avg. ' % (weeklygoal),
            rotation=29,            
            bbox=dict(boxstyle="square",
                       ec=(1, 1, 1),
                       fc=(1, 1, 1),
                       )
         )
    ax.grid(axis='y')
    if save_file:
        print('Saving trend file: ' + save_file)
        fig.savefig(save_file)

def parseDate(date_str):
    try: 
        date_bits = date_str.split('/')
        month = date_bits[0]
        day = date_bits[1]
        year = date_bits[2]
        date = ofxDT(datetime(int(year), int(month), int(day)))
    except:
        print('bad date provided')
        raise
    return date

def usage():
    print('spending_report.py ')
    print('   Required: ')
    print('            --institution <financial institution nickname>')
    print('   Optional')
    print('            --trend_file <a filename/path to save image>')
    print('            --ofx_file <an xml formatted ofx file>')
    print('            --start <date in mm/dd/yyyy>')
    print('            --end <date in mm/dd/yyyy>')
    print('            --config <path to ofxget config file>')
    print('            --goal <a spending amount for the week>')

def main(argv):
    institution = None
    trend_file = None
    ofx_file = None
    config = None
    goal = 500.00
    end = dtNowUtc()
    start = firstOfMonth(end)
    try:
        opts, args = getopt.getopt(argv,
                        "i:t:o:s:e:c:g:h:",
                        ["institution=",
                         "trend_file=",
                         "ofx_file=",
                         "start=",
                         "end=",
                         "config=",
                         "goal="]
        )
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-i', '--institution'):
            institution = arg
        elif opt in ("-t", "--trend_file"):
            trend_file = arg
        elif opt in ("-o", "--ofx_file"):
            ofx_file = arg
        elif opt in ("-s", "--start"):
            start = parseDate(arg)
        elif opt in ("-e", "--end"):
            end = parseDate(arg)
        elif opt in ("-c", "--config"):
            config = arg
        elif opt in ("-g", "--goal"):
            goal = arg
            
    if institution is None:
        print('institution not found in parameters. One must be provided')
        sys.exit(3)
        
    if config is None:
        config = findConfig()
        
    if ofx_file:
        stmt = stmtFromFile(ofx_file)
    else:
        stmt = stmtFromOFX(institution, start, end, config)
    
    allTrans = getTransactions( stmt, startDate=start) 
    print('All transactions since - %s' % (
        start.strftime('%a, %b %-d, %Y')
        )
    )
    printTrans(allTrans)
    balance = stmt.LEDGERBAL.BALAMT.text
    print('Total Balance: '+ str(makePositive(balance)))
    plotTrend(allTrans, weekly_goal=goal, save_file=trend_file)

if __name__ == "__main__":
    main(sys.argv[1:])
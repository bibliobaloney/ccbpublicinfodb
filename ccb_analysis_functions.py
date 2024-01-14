import sqlite3
from bs4 import BeautifulSoup
from datetime import date, timedelta
from calendar import monthrange

def makeinsertspan(id, stuff):
    thespan = '<span id="' + id + '">' + stuff + '</span>'
    thesoup = BeautifulSoup(thespan, features="html.parser")
    return thesoup

def makeinserttable(id, table):
    idstring = 'id="' + id + '"'
    newtable = table.replace('border="1"', idstring)
    thesoup = BeautifulSoup(newtable, features="html.parser")
    return thesoup

def makesortable(id, table):
    idstring = 'id="' + id + '"'
    newtable = table.replace('border="1"', idstring)
    sortabletable = newtable.replace('class="dataframe"', 'class="dataframe sortable"')
    thesoup = BeautifulSoup(sortabletable, features="html.parser")
    return thesoup

def makelinkcell(cell):
    celltext = cell.get_text(strip=True)
    if 'CCB' in celltext:
        link = 'https://dockets.ccb.gov/case/detail/' + celltext
        newcell = '<td><a href="' + link + '">' + celltext + '</a></td>'
        newsoup = BeautifulSoup(newcell, 'html.parser')
    return newsoup

def checkrepresentation(caselist):
    representedcases = []
    caseswithmultiplefirms = 0
    allfirms = []
    conn = sqlite3.connect("ccbdocsinfo.db")
    cur = conn.cursor()
    for case in caselist:
        casefirms = set()
        cur.execute('''SELECT ClaimantLawFirm FROM Claimants WHERE DocketNumber = ?''', (case, ))
        for row in cur:
            if row[0] is None:
                allfirms.append(row[0])
            else:
                casefirms.add(row[0])
        if len(casefirms) > 1:
            caseswithmultiplefirms += 1
        if len(casefirms) > 0:
            representedcases.append(case)
            for firm in casefirms:
                allfirms.append(firm)
    return (representedcases, caseswithmultiplefirms, allfirms)

def checkrepviacase(docketnum):
    conn = sqlite3.connect("ccbdocsinfo.db")
    cur = conn.cursor()
    cur.execute('''SELECT ClaimantLawFirm FROM Claimants WHERE DocketNumber = ?''', (docketnum, ))
    represented = 0
    for row in cur:
        if row[0] is not None:
            represented = 1
    return represented

def checkrepviadoc(documentnum):
    conn = sqlite3.connect("ccbdocsinfo.db")
    cur = conn.cursor()
    cur.execute('''SELECT DocketNumber from Documents WHERE DocumentNumber = ?''', (documentnum, ))
    for row in cur:
        docketnum = row[0]
    cur.execute('''SELECT ClaimantLawFirm FROM Claimants WHERE DocketNumber = ?''', (docketnum, ))
    represented = 0
    for row in cur:
        if row[0] is not None:
            represented = 1
    return represented

def last_dates_of_months(start_date, end_date):
    dateset = set()
    d = start_date
    while True:
        # Compute first and last dates of the month.
        month_start = d.replace(day = 1)
        n_days = monthrange(d.year, d.month)[1]
        month_end = d.replace(day = n_days)
        # Yield or break.
        if month_end <= end_date:
            dateset.add(month_end)
        else:
            break
        # Advance to a date in the next month.
        d = month_start + timedelta(days = 31)
    return dateset
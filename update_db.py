import requests, bs4, sqlite3
from pdfminer.high_level import extract_text
import ccbfunctions

# Connect to the db
try:
    conn = sqlite3.connect("ccbdocsinfo.db")
    cur = conn.cursor()
    print("Successfully connected to ccbdocsinfo.db")
except:
    print("Error connecting to ccbdocsinfo.db")

# Figure out the latest document already in the db
docswehave = []
cur.execute('SELECT DocumentNumber FROM Documents')
for row in cur:
    docswehave.append(row[0])
docswehave.sort()
latestdocindb = docswehave[-1]
print("latest doc we have =", latestdocindb)

# Get the new documents
hundredoffset = 0
moredocstoget = True
while moredocstoget == True:
    url = 'https://dockets.ccb.gov/search/documents?max=100&offset=' + str(hundredoffset) + '00'
    print('Getting page of documents:', hundredoffset)
    res = requests.get(url)
    res.raise_for_status()
    docsoup = bs4.BeautifulSoup(res.text, 'lxml')
    rowsonpage = docsoup.find_all('tr')
    newdocs = ccbfunctions.getdocsfromrows(rowsonpage)
    lastdoconpage = newdocs[-1][0]
    print("Last doc on page = ", lastdoconpage)
    cur.executemany("INSERT OR IGNORE INTO Documents VALUES (?, ?, ?, ?, ?, ?, ?)", newdocs)
    conn.commit()
    print(cur.rowcount, "documents added from CCB site to database")
    if lastdoconpage > (latestdocindb - 50):
        hundredoffset += 1
    else:
        moredocstoget = False

#Start adding claim info to Cases table
print("Dropping rows with no claim available last time; Adding any new publicly available claim URL info")
#First remove any rows previously added for cases that didn't have claims yet
cur.execute("DELETE from Cases WHERE (ClaimAvailableYN=0 AND Status IS NULL) OR (ClaimAvailableYN=0 AND Status!='Closed')")
conn.commit()
#Add Docket Number, Claim availability, and Claim URL for cases with publicly available initial claims
caseswithclaims = []
cur.execute('SELECT DocumentNumber, DocketNumber FROM Documents WHERE DocumentType="Claim" ORDER BY DocketNumber')
for row in cur:
    docketnum = row[1]
    claimurl = "https://dockets.ccb.gov/claim/view/" + str(row[0])
    newclaim = (docketnum, 1, claimurl, None, None, None, None, None, None, None, None, None, None)
    caseswithclaims.append(newclaim)
cur.executemany("INSERT OR IGNORE INTO Cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", caseswithclaims)
conn.commit()
print("Docket Number and URL for", cur.rowcount, "new claims added")

#Add any cases where the initial claim isn't available, but the amended claim is available
print("Adding documents where initial claim is not available but an amended claim is available")
amendedclaimonly = []
cur.execute("SELECT DocumentNumber, DocketNumber FROM Documents WHERE DocumentType='Amended Claim' ORDER BY FilingDate")
for row in cur:
    docketnum = row[1]
    claimurl = "https://dockets.ccb.gov/claim/view/" + str(row[0])
    newclaim = (docketnum, 1, claimurl, None, None, None, None, None, None, None, None, None, None)
    amendedclaimonly.append(newclaim)
cur.executemany("INSERT OR IGNORE INTO Cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", amendedclaimonly)
conn.commit()
print("Docket Number and URL for", cur.rowcount, "amended-claim-only claims added")

#Add any cases that have documents but no claim or amended claim
docketswithclaims = set()
cur.execute('SELECT DocketNumber FROM Cases')
for row in cur:
    docketswithclaims.add(row[0])
noclaimavailableset = set()
cur.execute('SELECT DocketNumber FROM Documents')
for row in cur:
    if row[0] not in docketswithclaims:
        noclaimavailableset.add(row[0])
noclaimavailable = list(noclaimavailableset)
noclaimavailable.sort()
noclaimdockets = []
for case in noclaimavailable:
    newrow = (case, 0, None, None, None, None, None, None, None, None, None, None, None)
    noclaimdockets.append(newrow)
cur.executemany("INSERT OR IGNORE INTO Cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", noclaimdockets)
conn.commit()
print(cur.rowcount, "docket numbers added for cases with documents but no claim available")

#Add claim info (case, claimants, respondents, works) for all cases where claims are available and we haven't done that yet
claiminfotoadd = []
claimantinfotoadd = []
respondentinfotoadd = []
worksinfotoadd = []
cur.execute('SELECT DocketNumber, ClaimURL FROM Cases WHERE ClaimAvailableYN = 1 AND SmallerYN IS NULL')
for row in cur:
    docketnum = row[0]
    url = row[1]
    print("Getting info about claim and claimant for", docketnum)
    res = requests.get(url)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    newclaiminfo = ccbfunctions.claimtypesanddescriptions(soup)
    plusupdateinfo = (newclaiminfo[0], newclaiminfo[1], newclaiminfo[2], newclaiminfo[3], newclaiminfo[4], newclaiminfo[5], 
                      newclaiminfo[6], newclaiminfo[7], newclaiminfo[8], docketnum)
    claiminfotoadd.append(plusupdateinfo)
    claimantinfoinclaim = ccbfunctions.getclaimantinfo(soup)
    for claimant in claimantinfoinclaim:
        plusclaimantupdateinfo = (docketnum, claimant[0], claimant[1], claimant[2], claimant[3], claimant[4],
                          claimant[5])
        claimantinfotoadd.append(plusclaimantupdateinfo)
    print("Getting info about respondents for", docketnum)
    listofrespondents = ccbfunctions.checkrespondents(docketnum)
    for respondent in listofrespondents:
        plusrespupdateinfo = (docketnum, respondent[0], respondent[1], respondent[2], respondent[3])
        respondentinfotoadd.append(plusrespupdateinfo)
    if newclaiminfo[1] == 1:
        worksinfoinclaim = ccbfunctions.getworks(soup)
        for work in worksinfoinclaim:
            plusworkupdateinfo = (docketnum, work[0], work[1], work[2], work[3], work[4], work[5], work[6], work[7], work[8])
            worksinfotoadd.append(plusworkupdateinfo)
print("Adding info about claim to database")
cur.executemany('''UPDATE Cases SET SmallerYN = ?, InfringementYN = ?, InfringementDescription = ?, InfringementRelief = ?, 
                NoninfringementYN = ?, NoninfringementDescription = ?, DmcaYN = ?, DmcaDescription = ?, DmcaRelief = ? 
                WHERE DocketNumber = ?''', claiminfotoadd)
conn.commit()
print("Basic claim info added for", cur.rowcount, "claims")
print("Adding info about claimants to database")
cur.executemany('''INSERT INTO Claimants VALUES (?, ?, ?, ?, ?, ?, ?)''', claimantinfotoadd)
conn.commit()
print("Claimant info added for", cur.rowcount, "claimants")
print("Adding info about respondents to database")
cur.executemany('''INSERT INTO Respondents VALUES (?, ?, ?, ?, ?)''', respondentinfotoadd)
conn.commit()
print("Respondent info added for", cur.rowcount, "respondents")
print("Adding info about works to database")
cur.executemany('''INSERT INTO Works VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', worksinfotoadd)
conn.commit()
print("Works info added for", cur.rowcount, "works")

#Get a list of dismissals already in the Dismissals table, in case you've been here before
olderdismissals = []
cur.execute('SELECT DocumentNumber from Dismissals')
for row in cur:
    olderdismissals.append(row[0])

#Get a list of all dismissal orders from the db's Documents table
dismissals = []
cur.execute('SELECT DocumentNumber from Documents WHERE DocumentType LIKE "Order Dismissing Clai%"')
for row in cur:
    dismissals.append(row[0])

#Compare to get just the new ones, because downloading pdfs is slow
newdismissals = [x for x in dismissals if x not in olderdismissals]
print("This run should add", str(len(newdismissals)), "orders")

dismissalinfolist = []
for documentnum in newdismissals:
    print('Getting and reading dissmissal order', documentnum)
    ccbfunctions.getdocumentpdf(documentnum)
    localfile = 'pdfs/' + str(documentnum) + '.pdf'
    ordertext = extract_text(localfile)
    ordertext = ordertext.replace('\n', '')
    ordertext = ordertext.replace('  ', ' ')
    settlement = 0
    if 'settlement' in ordertext:
        settlement = 1
    prej = ccbfunctions.checkprejudice(ordertext)
    reasons = ccbfunctions.getdismissalreasons(ordertext)
    if len(reasons) == 1 and (prej == 0 or prej ==1):
        dismissalinfo = (documentnum, 0, prej, settlement, reasons[0], None)
    else:
        dismissalinfo = ccbfunctions.humandismissalinfo(documentnum, ordertext)
    dismissalinfolist.append(dismissalinfo)

print("Adding info about dismissals to database")
cur.executemany('''INSERT OR IGNORE INTO Dismissals VALUES (?, ?, ?, ?, ?, ?)''', dismissalinfolist)
conn.commit()
print("Dismissal info added for", cur.rowcount, "orders")

# HERE BEGINS code for updating the Orders to Amend table
#Get a list of document numbers and reasons already in the OrdersToAmend table, in case you've been here before
olderotas = []
allthereasons = []
cur.execute('SELECT * from OrdersToAmend')
for row in cur:
    olderotas.append(row[0])
    allthereasons.append(row[1])

#Get a list of document numbers for all the Orders to Amend in the Documents table
otas = []
cur.execute('SELECT DocumentNumber from Documents WHERE DocumentType LIKE "Order to Amend%"')
for row in cur:
    otas.append(row[0])

#Compare to get just the new ones, because downloading pdfs is slow
newotas = [x for x in otas if x not in olderotas]

#Fonts used for bold "reason" headings since late January 2023, e.g. document 1856
stylesa = ["font-family: Garamond-Bold; font-size:12px", "font-family: Garamond-Bold; font-size:11px",
               "font-family: F3; font-size:11px"]
#Fonts used for bold "reason" headings before 1/20/2023, e.g. document 1803
stylesb = ["font-family: Cambria-Bold; font-size:8px", "font-family: Cambria-Bold; font-size:9px",
           "font-family: Cambria,Bold; font-size:9px", "font-family: Times-Bold; font-size:9px", 
           "font-family: TimesNewRomanPS-BoldMT; font-size:9px", 
           "font-family: TimesNewRomanPS-BoldMT; font-size:8px",]

otainfolist = []
notreasons = {}
nothingfound = []
for documentnum in newotas:
    print(documentnum)
    ccbfunctions.getdocumentpdf(documentnum)
    ordersoup = ccbfunctions.pdftosoup(documentnum)
    spanstocheck = ccbfunctions.getboldspans(ordersoup, stylesa)
    likelyreasons = ccbfunctions.getlikelyreasons(spanstocheck)
    sortedreasons = ccbfunctions.checkreasons(likelyreasons, allthereasons)
    if len(sortedreasons[0]) == 0:
        spanstocheck = ccbfunctions.getboldspans(ordersoup, stylesb)
        likelyreasons = ccbfunctions.getlikelyreasons(spanstocheck)
        sortedreasons = ccbfunctions.checkreasons(likelyreasons, allthereasons)
    if len(sortedreasons[0]) == 0:
        nothingfound.append(documentnum)
    else:
        approved = sortedreasons[0]
        allthereasons.extend(approved)
    newrejectedreasons = sortedreasons[1]
    if len(newrejectedreasons) > 0:
        notreasons[documentnum] = newrejectedreasons
    print(approved)
    for reason in approved:
        otainfolist.append((documentnum, reason))

print("New not-reasons:")
for order in notreasons:
    print(order)
    print(notreasons[order])

print("Adding info about Orders to Amend to database")
cur.executemany('''INSERT OR IGNORE INTO OrdersToAmend VALUES (?, ?)''', otainfolist)
conn.commit()
print("OTA info added for", cur.rowcount, "reasons")

print('Number of new Orders to Amend found at the beginning of this run:', len(newotas))
print('No reasons wree found in this many of the orders checked:', len(nothingfound))
print(nothingfound)
# HERE ENDS code for updating the OrdersToAmend table

# Get new final determinations
print('Getting new Final Determinations')
# Get a list of Final Determinations already in the FinalDeterminations table
oldfds = []
cur.execute('''Select DocumentNumber from FinalDeterminations''')
for row in cur:
    oldfds.append(row[0])

# Get a list of all the Final Determinations in the Documents table
allfinaldeterminations = []
cur.execute('''SELECT DocketNumber, DocumentNumber, DocumentType from Documents 
            WHERE DocumentType LIKE "Final Determination%"''')
for row in cur:
    allfinaldeterminations.append(row)

#Compare to get just the new ones, because downloading pdfs is slow
newfds = [x for x in allfinaldeterminations if x[1] not in oldfds]

fdsinfolist = []
for fdrow in newfds:
    documentnum = fdrow[1]
    damages = ccbfunctions.getdamages(documentnum)
    docketnum = fdrow[0]
    print(docketnum, 'Docuement number', documentnum)
    isdefault = ccbfunctions.checkdefault(docketnum)
    fdsinfolist.append((documentnum, isdefault, damages))

print("Adding info about Final Determinations to database")
cur.executemany('''INSERT OR IGNORE INTO FinalDeterminations VALUES (?, ?, ?)''', fdsinfolist)
conn.commit()
print("Final Determination info added for", cur.rowcount, "FDs")

# Get a list of cases to check statuses for
cases = []
cur.execute('''SELECT DocketNumber FROM Cases''')
for row in cur:
    cases.append(row[0])
# Collect the statuses
statuslist = []
for case in cases:
    status = ccbfunctions.getstatus(case)
    statuslist.append((status, case))
# Update the statuses

cur.executemany('''UPDATE Cases SET Status = ? WHERE DocketNumber = ?''', statuslist)
conn.commit()
print("Status updated for", cur.rowcount, "dockets")

cur.close()

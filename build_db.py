import requests, bs4, sqlite3
from pdfminer.high_level import extract_text
import ccbfunctions

# Connect to the db, create it if it doesn't exist yet
try:
    conn = sqlite3.connect("ccbdocstest.db")
    cur = conn.cursor()
    print("Successfully connected to ccbdocstest.db")
except:
    print("Error connecting to ccbdocstest.db")

#In case you're running this for the first time or decided to restructure this table    
docsrebuild = input('Do you want to (re)build the Documents table from scratch (y/n)?')
if docsrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Documents')
    try:
        docs_table_query = '''CREATE TABLE Documents (DocumentNumber INTEGER UNIQUE, DocketNumber TEXT, 
        DocumentTitle TEXT, DocumentType TEXT, DocumentParty TEXT, DateFiledString TEXT, FilingDate datetime)'''
        cur.execute(docs_table_query)
        conn.commit()
        print("Docuuments table freshly created")
    except sqlite3.Error as error:
        print("Error while creating documents table:", error)
else:
    print('Okay, skipping drop and rebuild Documents')

#Test to see if we can add just a few documents
getlatesttwenty = input("Do you want to add the most recent 20 documents (y/n)?")
if getlatesttwenty == 'y':
    print("Getting 20 most recent documents")
    starterdocs = ccbfunctions.getpageofdocs("https://dockets.ccb.gov/search/documents")
    cur.executemany("INSERT OR IGNORE INTO Documents VALUES (?, ?, ?, ?, ?, ?, ?)", starterdocs)
    conn.commit()
    print(cur.rowcount, "of 20 most recent documents added to Documents table")
else:
    print("Okay, not adding those 20 right now")

#Test to see if we can add a few more documents
getlatesthundred = input("Do you want to add the most recent 100 (y/n)?")
if getlatesthundred == 'y':
    print("Getting 100 most recent documents")
    mostrecenthundred = ccbfunctions.getpageofdocs("https://dockets.ccb.gov/search/documents?max=100")
    cur.executemany("INSERT OR IGNORE INTO Documents VALUES (?, ?, ?, ?, ?, ?, ?)", mostrecenthundred)
    conn.commit()
    print(cur.rowcount, "of 100 most recent documents added")

#Really get all the documents
getallthedocs = input("Do you want to grab the info on ALL the documents (y/n)?")
if getallthedocs == 'y':
    hundredoffset = 0
    moredocstoget = True
    while moredocstoget == True:
        url = 'https://dockets.ccb.gov/search/documents?max=100&offset=' + str(hundredoffset) + '00'
        res = requests.get(url)
        res.raise_for_status()
        docsoup = bs4.BeautifulSoup(res.text, 'lxml')
        rowsonpage = docsoup.find_all('tr')
        if len(rowsonpage) == 0:
            print('No more pages of documents')
            break
        else:
            newdocs = ccbfunctions.getdocsfromrows(rowsonpage)
            hundredoffset += 1
            print('Getting page of documents:', hundredoffset)
            cur.executemany("INSERT OR IGNORE INTO Documents VALUES (?, ?, ?, ?, ?, ?, ?)", newdocs)
            conn.commit()
    print(cur.rowcount, "documents added from CCB site to database")
else:
    print("Okay, not fetching thousands of docs")

#Build the Cases table, or drop and rebuild it
casesrebuild = input('Do you want to (re)build the Cases table from scratch (y/n)?')
if casesrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Cases')
    try:
        cases_table_query = '''CREATE TABLE Cases (DocketNumber TEXT UNIQUE, ClaimAvailableYN INTEGER, ClaimURL TEXT, 
        SmallerYN INTEGER, InfringementYN INTEGER, InfringementDescription TEXT, InfringementRelief TEXT, 
        NoninfringementYN INTEGER, NoninfringementDescription TEXT, DmcaYN INTEGER, DmcaDescription TEXT, 
        DmcaRelief TEXT, Status TEXT)'''
        cur.execute(cases_table_query)
        conn.commit()
        print("Cases table freshly created")
    except sqlite3.Error as error:
        print("Error while creating cases table:", error)
else:
    print('Okay, skipping drop and rebuild Cases table')

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

#In case you're running this for the first time or decided to restructure Claimants table    
docsrebuild = input('Do you want to (re)build the Claimants table from scratch (y/n)?')
if docsrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Claimants')
    try:
        claimants_table_query = '''CREATE TABLE Claimants (DocketNumber TEXT, ClaimantName TEXT, ClaimantCity TEXT, 
        ClaimantStateOrCountry TEXT, Country TEXT, ClaimantRepresentative TEXT, ClaimantLawFirm TEXT)'''
        cur.execute(claimants_table_query)
        conn.commit()
        print("Claimants table freshly created")
    except sqlite3.Error as error:
        print("Possible error while creating claimants table:", error)
else:
    print('Okay, skipping drop and rebuild Claimants')

#In case you're running this for the first time or decided to restructure Respondents table    
docsrebuild = input('Do you want to (re)build the Respondents table from scratch (y/n)?')
if docsrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Respondents')
    try:
        respondents_table_query = '''CREATE TABLE Respondents (DocketNumber TEXT, RespondentName TEXT, 
        RespondentRepresentative TEXT, RespondentLawFirm TEXT, OptedOutYN INTEGER)'''
        cur.execute(respondents_table_query)
        conn.commit()
        print("Respondents table freshly created")
    except sqlite3.Error as error:
        print("Possible error while creating Respondents table:", error)
else:
    print('Okay, skipping drop and rebuild Respondents')

#In case you're running this for the first time or decided to restructure the table of works in infringement claims  
docsrebuild = input('Do you want to (re)build the Works table from scratch (y/n)?')
if docsrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Works')
    try:
        works_table_query = '''CREATE TABLE Works (DocketNumber TEXT, Title TEXT, Authors TEXT, CoOwners TEXT, RegisteredYN INTEGER, 
        RegistrationNumber TEXT, RegistrationDate datetime, RequestNumber TEXT, WorkType TEXT, WorkDescription TEXT)'''
        cur.execute(works_table_query)
        conn.commit()
        print("Works table freshly created")
    except sqlite3.Error as error:
        print("Possible error while creating Works table:", error)
else:
    print('Okay, skipping drop and rebuild Works')

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

#In case you're running this for the first time or decided to restructure the Dismissals table
docsrebuild = input('Do you want to (re)build the Dismissals table from scratch (y/n)?')
if docsrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS Dismissals')
    try:
        dismissals_table_query = '''CREATE TABLE Dismissals (DocumentNumber INTEGER UNIQUE, HumanReadYN INTEGER,
        WithPrejudice INTEGER, SettlementYN INTEGER, Reason1 TEXT, Reason2 TEXT)'''
        cur.execute(dismissals_table_query)
        conn.commit()
        print("Dissmissals table freshly created")
    except sqlite3.Error as error:
        print("Possible error while creating Works table:", error)
else:
    print('Okay, skipping drop and rebuild Dismissals')

#Get a list of dismissals already in the Dismissals table, in case you've been here beforfe
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

cur.close()

import bs4, sqlite3
import statistics
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import ccb_analysis_functions
import ccbfunctions
import pandas as pd
import plotly.express as px
#datetime import is for strftime, used in big bar chart at end of this script

# Save some strings and things to use later
startafile = '<!DOCTYPE html><html><head></head><body>' + '\n'
endafile = '</body></html>'
ccbstart = date.fromisoformat('2022-06-16')
thirtydaysago = date.today() - timedelta(days=30)
sixtydaysago = date.today() - timedelta(days=60)
ccbanniversary = date.fromisoformat('2023-06-16')
secondanniversary = date.fromisoformat('2024-06-16')
thirdanniversary = date.fromisoformat('2025-06-06')

# Connect to the database
print('Connecting to the database...')
conn = sqlite3.connect('ccbdocsinfo.db')
cur = conn.cursor()
print('Connected')

# Make some lists
allclaims=[]
cur.execute('''SELECT DocketNumber FROM Cases WHERE ClaimAvailableYN = 1''')
for row in cur:
    allclaims.append(row[0])

allcases = []
cur.execute('''SELECT DocketNumber from Cases''')
for row in cur:
    allcases.append(row[0])

recentclaims = []
firstyearclaims = []
secondyearclaims = []
thirdyearclaims = []
for case in allclaims:
    cur.execute('''SELECT FilingDate FROM Documents WHERE DocketNumber = ? AND 
                    (DocumentType = "Claim" OR DocumentType = "Amended Claim")''', (case, ))
    claimdates = []
    for row in cur:
        claimdates.append(row[0])
    claimdates.sort()
    d1 = date.fromisoformat(claimdates[0])
    if d1 > sixtydaysago:
        recentclaims.append(case)
    if d1 < thirdanniversary and d1 >= secondanniversary:
        thirdyearclaims.append(case)
    elif d1 < secondanniversary and d1 >= ccbanniversary:
        secondyearclaims.append(case)
    elif d1 < ccbanniversary:
        firstyearclaims.append(case)

# Read the existing file
existingtablespage = open("../bibliobaloney.github.io/index.html", "r", encoding='utf-8')
html = existingtablespage.read()
soup = bs4.BeautifulSoup(html, features="html.parser")
existingtablespage.close()

#Create a searchable file of narratives from infringement claims
cur.execute('''SELECT DocketNumber, Caption, ClaimURL, InfringementDescription, InfringementRelief 
            FROM Cases WHERE InfringementYN = 1 ORDER BY DocketNumber DESC''')
infringementdescriptions = []
for row in cur:
    infringementdescriptions.append(row)
df = pd.DataFrame(infringementdescriptions, columns =['Docket Number', 'Caption', 'Claim URL', 
                                                      'Describe the infringement', 'Relief sought'])
df.to_csv('../bibliobaloney.github.io/infringementdescriptions.csv', index=False)

#Create a searchable file of narratives from noninfringement claims
cur.execute('''SELECT DocketNumber, Caption, ClaimURL, NoninfringementDescription 
            FROM Cases WHERE NoninfringementYN = 1 ORDER BY DocketNumber DESC''')
noninfringementdescriptions = []
for row in cur:
    noninfringementdescriptions.append(row)
df = pd.DataFrame(noninfringementdescriptions, columns =['Docket Number', 'Caption', 'Claim URL', 
                                                      'Describe dispute with respondent(s)'])
df.to_csv('../bibliobaloney.github.io/noninfringementdescriptions.csv', index=False)

#Create a searchable file of narratives from DMCA claims
cur.execute('''SELECT DocketNumber, Caption, ClaimURL, DmcaDescription, DmcaRelief 
            FROM Cases WHERE DmcaYN = 1 ORDER BY DocketNumber DESC''')
dmcadescriptions = []
for row in cur:
    dmcadescriptions.append(row)
df = pd.DataFrame(dmcadescriptions, columns =['Docket Number', 'Caption', 'Claim URL', 
                                                      'Explanation of the Misrepresentation', 
                                                      'Relief sought'])
df.to_csv('../bibliobaloney.github.io/dmcadescriptions.csv', index=False)

# Update the final determindations table
cur.execute('''SELECT * FROM FinalDeterminations JOIN Documents USING(DocumentNumber) 
            ORDER BY FilingDate DESC''')
fdresults = []
fdcases = []
fdcaseinfo = dict()
for row in cur:
    fdresults.append(list(row))
for result in fdresults:
    docketnum = result[3]
    fdcases.append(docketnum)
    cur.execute('''SELECT FilingDate FROM Documents WHERE DocketNumber = ? and 
                (DocumentType = 'Claim' or DocumentType = 'Amended Claim')''', (docketnum, ))
    claimdates = []
    for row in cur:
        claimdates.append(row[0])
    claimdates.sort()
    oldestclaimdate = claimdates[0]
    result.append(oldestclaimdate)
    fdtype = result[5]
    defaultyn = result[1]
    if defaultyn == 1:
        fdtype = 'Default'
    elif 'Settlement' in fdtype:
        fdtype = 'Settlement'
    elif 'Dismissal' in fdtype:
        fdtype = 'Dismissal'
    damages = result[2]
    if damages is None:
        damages = 'No information provided'
    else:
        damages = str(damages)
    claimantrepinfo = ccb_analysis_functions.checkrepresentation([docketnum])
    claimantrepyn = 'No'
    if len(claimantrepinfo[0]) > 0:
        claimantrepyn = 'Yes'
    fddate = date.fromisoformat(result[8])
    claimdate = date.fromisoformat(result[9])
    daystofd = (fddate-claimdate).days
    cur.execute('''SELECT Caption from Cases WHERE DocketNumber = ?''', (docketnum, ))
    for row in cur:
        caption = row[0]
    fdcaseinfo[docketnum] = [caption, fdtype, damages, claimantrepyn, fddate, daystofd]

tableheaders = ['Caption', 'Determination type', 'Damages', 'Claimant represented?', 
                'Date', 'Case duration (days)']
determindationsdf = pd.DataFrame.from_dict(fdcaseinfo, orient='index', columns=tableheaders)
dftable = determindationsdf.to_html(justify='center')
dftable = dftable.replace('<th></th>', '<th>Docket Number</th>')
dftablesoup = ccb_analysis_functions.makesortable('fdstable', dftable)
headercells = dftablesoup.find_all('th')
for cell in headercells:
    celltext = cell.get_text(strip=True)
    if 'CCB' in celltext:
        newcell = ccb_analysis_functions.makelinkcell(cell)
        cell.replace_with(newcell)
oldfdtable = soup.find(id='fdstable')
oldfdtable.replace_with(dftablesoup)

# Update the rundate, which appears in 2 locations
rundate = str(date.today())
datespans = soup.find_all(id="rundate")
for span in datespans:
    span.string.replace_with(rundate)

# Update the number of final determinations, which appears in 2 locations
strnumfds = str(len(fdcases))
fdcountspans = soup.find_all(id="fdscount")
for span in fdcountspans:
    span.string.replace_with(strnumfds)

### Active cases
# Get a list of active cases
activecases = []
cur.execute('''SELECT DocketNumber FROM Cases WHERE Status = "Active Phase"''')
for row in cur:
    activecases.append(row[0])
numactivecases = str(len(activecases))

# Create a page that lists all the active cases, and links to them
with open("../bibliobaloney.github.io/activecasesbarelist.html", "w", encoding='utf-8') as outf:
    outf.write(startafile)
    for case in activecases:
        outf.write('<a href="https://dockets.ccb.gov/case/detail/' + case + '">' + case + '</a>' + '<br />')
        outf.write(endafile)
outf.close()

# Add the number of active cases to the page, link to the active pages list
totalactivespan = soup.find(id="numactivecases")
linkednumberhtml = ('<a href="activecasesbarelist.html">' + str(numactivecases) + '</a>')
linkednumber = ccb_analysis_functions.makeinsertspan('numactivecases', linkednumberhtml)
totalactivespan.replace_with(linkednumber)

# Calculate the average number of days the active cases have been open, and add it to the page
timestoactive = []
for case in activecases:
    schedorders = []
    claims = []
    cur.execute('''SELECT DocumentType, FilingDate FROM Documents WHERE DocketNumber = ?''', (case, ))
    for row in cur:
        if row[0] == 'Scheduling Order':
            schedorders.append((row[1], row[0]))
        if row[0] == 'Claim' or row[0] == 'Amended Claim':
            claims.append((row[1], row[0]))
    schedorders.sort()
    claims.sort()
    d1 = date.fromisoformat(claims[0][0])
    d2 = date.fromisoformat(schedorders[0][0])
    daysfromclaimtoactive = (d2-d1).days
    timestoactive.append(daysfromclaimtoactive)
avgtimetoactive = str(round(statistics.mean(timestoactive)))
timetoinsert = ccb_analysis_functions.makeinsertspan('avgdaysactivecasesopen', avgtimetoactive)
oldtimetoactivespan = soup.find(id="avgdaysactivecasesopen")
oldtimetoactivespan.replace_with(timetoinsert)

# Calculate the number of types of each type of claim in the active cases, add it to page in a table
listclaimtypes = []
for case in activecases:
    cur.execute('''SELECT InfringementYN, NoninfringementYN, DmcaYN FROM Cases WHERE DocketNumber = ?''', (case, ))
    for row in cur:
        claimtypes = []
        if row[0] == 1:
            claimtypes.append('Infringement')
        if row[1] == 1:
            claimtypes.append('Noninfringement')
        if row[2] == 1:
            claimtypes.append('DMCA Misrepresentation')
        stringofclaims = ', '.join(claimtypes)
        listclaimtypes.append(stringofclaims)
activeclaimstypes = pd.Series(data=listclaimtypes)
df = activeclaimstypes.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
activetypestoinsert = ccb_analysis_functions.makeinserttable('activeclaimtypes', html_table)
oldactivetypes = soup.find(id='activeclaimtypes')
oldactivetypes.replace_with(activetypestoinsert)

# Calculate how many active cases are on the road to default
participatingrespondents = []
for case in activecases:
    yesnomaybe = ccbfunctions.checkdefault(case)
    if yesnomaybe == 0:
        participatingrespondents.append('Yes')
    elif yesnomaybe == 1:
        participatingrespondents.append('No')
    else:
        participatingrespondents.append("It's complicated")
participatingseries = pd.Series(data=participatingrespondents)
df = participatingseries.value_counts().rename_axis('Any filings by respondent?').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
potentialdefaulttoinsert = ccb_analysis_functions.makeinserttable('roadtodefault', html_table)
oldpotentialdefault = soup.find(id='roadtodefault')
oldpotentialdefault.replace_with(potentialdefaulttoinsert)

# Calculate how many of the active claims were filed by represented claimants
representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(activecases)
activerepaspercent = format((len(representedcases)/len(activecases)), ".0%")
activemultiplefirms = str(caseswithmultiplefirms)
activecasefirms = []
for item in allfirms:
    if item is None:
        activecasefirms.append('No law firm')
    else:
        activecasefirms.append(item)
activefirmsseries = pd.Series(data=activecasefirms)
df = activefirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')

# Update the data about representation for active cases
pctspan = soup.find(id="pctactiverep")
pctspan.string.replace_with(activerepaspercent)
multiplespan = soup.find(id="multiplerep")
multiplespan.string.replace_with(activemultiplefirms)
tablesoup = ccb_analysis_functions.makeinserttable('activerepresentation', html_table)
activereptable = soup.find(id="activerepresentation")
activereptable.replace_with(tablesoup)

# Calculate representation for active cases plus formerly active cases
everactive = fdcases + activecases
representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(everactive)
activerepaspercent = format((len(representedcases)/len(activecases)), ".0%")
activemultiplefirms = str(caseswithmultiplefirms)
activecasefirms = []
for item in allfirms:
    if item is None:
        activecasefirms.append('No law firm')
    else:
        activecasefirms.append(item)
activefirmsseries = pd.Series(data=activecasefirms)
df = activefirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')

# Update the data about representation for active cases
pctspan = soup.find(id="pcteveractiverep")
pctspan.string.replace_with(activerepaspercent)
multiplespan = soup.find(id="everactivemultiplerep")
multiplespan.string.replace_with(activemultiplefirms)
tablesoup = ccb_analysis_functions.makeinserttable('everactiverepresentation', html_table)
activereptable = soup.find(id="everactiverepresentation")
activereptable.replace_with(tablesoup)

# Info on representation for all claims is calculated with the All Claims stuff, and updated 
# in multiple places on the page

### Open cases
# Update status of open (non-active) cases
openstatuses=[]
cur.execute('''SELECT Status FROM Cases WHERE Status IN ('Waiting for Proof of Service', 
            'Waiting for Review of Amended Claim', 'Waiting for Amended Claim', 
            'Waiting for Scheduling Order/Expiration of Opt Out Window', 'In Abeyance', 'Waiting for Initial Review')''')
for row in cur:
    openstatuses.append(row[0])
openstatusseries = pd.Series(data=openstatuses)
df = openstatusseries.value_counts().rename_axis('Status').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
html_table.replace('border="1"', 'id="opencasestatus"')
tablesoup = ccb_analysis_functions.makeinserttable('opencasestatus', html_table)
openstatustable = soup.find(id="opencasestatus")
openstatustable.replace_with(tablesoup)

### Dismissed Cases
# Update reasons for Dismissals
# For all the dissmissals
allthereasons, dismissalreasonsrep, dismissalreasonsunrep = [], [], []
cur.execute('''SELECT DocumentNumber, Reason1, Reason2 FROM Dismissals''')
for row in cur:
    documentnum = row[0]
    reason = row[1]
    secondreason = row[2]
    allthereasons.append(reason)
    rep = ccb_analysis_functions.checkrepviadoc(documentnum)
    if rep == 0:
        dismissalreasonsunrep.append(reason)
    elif rep == 1:
        dismissalreasonsrep.append(reason)
    if secondreason != None:
        allthereasons.append(secondreason)
        if rep == 0:
            dismissalreasonsunrep.append(secondreason)
        elif rep ==1:
            dismissalreasonsrep.append(secondreason)
reasonseries = pd.Series(data=allthereasons)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsall', html_table)
prevtable = soup.find(id="dismissalreasonsall")
prevtable.replace_with(tablesoup)
# Update the chart for all dismissals
fig = px.pie(df, values='Orders', names='Reasons')
fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    )
fig.write_html("../bibliobaloney.github.io/charts/alldismissals.html", include_plotlyjs='directory')

# Represented and unrepresented, all dismissal reasons
reasonseries = pd.Series(data=dismissalreasonsrep)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrep', html_table)
prevtable = soup.find(id="dismissalreasonsrep")
prevtable.replace_with(tablesoup)
reasonseries = pd.Series(data=dismissalreasonsunrep)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsunrep', html_table)
prevtable = soup.find(id="dismissalreasonsunrep")
prevtable.replace_with(tablesoup)

# For the recent dismissals
recentreasons, dismissalreasonsrecentrep, dismissalreasonsrecentunrep = [], [], []
cur.execute('''SELECT DocumentNumber, Reason1, Reason2 FROM Dismissals JOIN Documents USING(DocumentNumber) 
            WHERE Documents.FilingDate > date("now", "-60 days")''')
for row in cur:
    documentnum = row[0]
    reason = row[1]
    secondreason = row[2]
    recentreasons.append(reason)
    rep = ccb_analysis_functions.checkrepviadoc(documentnum)
    if rep == 0:
        dismissalreasonsrecentunrep.append(reason)
    elif rep == 1:
        dismissalreasonsrecentrep.append(reason)
    if secondreason != None:
        recentreasons.append(secondreason)
        if rep == 0:
            dismissalreasonsrecentunrep.append(secondreason)
        elif rep ==1:
            dismissalreasonsrecentrep.append(secondreason)
reasonseries = pd.Series(data=recentreasons)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrecent', html_table)
prevtable = soup.find(id="dismissalreasonsrecent")
prevtable.replace_with(tablesoup)
#Represented claimants
reasonseries = pd.Series(data=dismissalreasonsrecentrep)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrecentrep', html_table)
prevtable = soup.find(id="dismissalreasonsrecentrep")
prevtable.replace_with(tablesoup)
#Unepresented claimants
reasonseries = pd.Series(data=dismissalreasonsrecentunrep)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrecentunrep', html_table)
prevtable = soup.find(id="dismissalreasonsrecentunrep")
prevtable.replace_with(tablesoup)

# For dismissals from the third year, for comparison
cur.execute('''SELECT DocumentNumber, Reason1, Reason2 FROM Dismissals JOIN Documents USING(DocumentNumber) 
            WHERE Documents.FilingDate < date("2025-06-16") AND Documents.FilingDate >= date("2024-06-16")''')
reasonsthirdyear, dismissalreasonsrepyearthree, dismissalreasonsunrepyearthree = [], [], []
for row in cur:
    documentnum = row[0]
    reason = row[1]
    secondreason = row[2]
    reasonsthirdyear.append(reason)
    rep = ccb_analysis_functions.checkrepviadoc(documentnum)
    if rep == 0:
        dismissalreasonsunrepyearthree.append(reason)
    elif rep == 1:
        dismissalreasonsrepyearthree.append(reason)
    if secondreason != None:
        reasonsthirdyear.append(secondreason)
        if rep == 0:
            dismissalreasonsunrepyearthree.append(secondreason)
        elif rep ==1:
            dismissalreasonsrepyearthree.append(secondreason)
reasonseries = pd.Series(data=reasonsthirdyear)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsyearthree', html_table)
prevtable = soup.find(id="dismissalreasonsyearthree")
prevtable.replace_with(tablesoup)
reasonseries = pd.Series(data=dismissalreasonsrepyearthree)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrepyearthree', html_table)
prevtable = soup.find(id="dismissalreasonsrepyearthree")
prevtable.replace_with(tablesoup)
reasonseries = pd.Series(data=dismissalreasonsunrepyearthree)
df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
html_table = df.to_html(index=False, justify='center')
tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsunrepyearthree', html_table)
prevtable = soup.find(id="dismissalreasonsunrepyearthree")
prevtable.replace_with(tablesoup)

# For dismissals from the second year, for comparison
# Does not need to run every week
# cur.execute('''SELECT DocumentNumber, Reason1, Reason2 FROM Dismissals JOIN Documents USING(DocumentNumber) 
#             WHERE Documents.FilingDate < date("2024-06-16") AND Documents.FilingDate >= date("2023-06-16")''')
# reasonssecondyear, dismissalreasonsrepyeartwo, dismissalreasonsunrepyeartwo = [], [], []
# for row in cur:
#     documentnum = row[0]
#     reason = row[1]
#     secondreason = row[2]
#     reasonssecondyear.append(reason)
#     rep = ccb_analysis_functions.checkrepviadoc(documentnum)
#     if rep == 0:
#         dismissalreasonsunrepyeartwo.append(reason)
#     elif rep == 1:
#         dismissalreasonsrepyeartwo.append(reason)
#     if secondreason != None:
#         reasonssecondyear.append(secondreason)
#         if rep == 0:
#             dismissalreasonsunrepyeartwo.append(secondreason)
#         elif rep ==1:
#             dismissalreasonsrepyeartwo.append(secondreason)
# reasonseries = pd.Series(data=reasonssecondyear)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsyeartwo', html_table)
# prevtable = soup.find(id="dismissalreasonsyeartwo")
# prevtable.replace_with(tablesoup)
# reasonseries = pd.Series(data=dismissalreasonsrepyeartwo)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrepyeartwo', html_table)
# prevtable = soup.find(id="dismissalreasonsrepyeartwo")
# prevtable.replace_with(tablesoup)
# reasonseries = pd.Series(data=dismissalreasonsunrepyeartwo)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsunrepyeartwo', html_table)
# prevtable = soup.find(id="dismissalreasonsunrepyeartwo")
# prevtable.replace_with(tablesoup)

# For dismissals from the first year, for comparison
## Does not need to run every week
# cur.execute('''SELECT DocumentNumber, Reason1, Reason2 FROM Dismissals JOIN Documents USING(DocumentNumber) 
#             WHERE Documents.FilingDate < date("2023-06-16")''')
# reasonsfirstyear, dismissalreasonsrepold, dismissalreasonsunrepold = [], [], []
# for row in cur:
#     documentnum = row[0]
#     reason = row[1]
#     secondreason = row[2]
#     reasonsfirstyear.append(reason)
#     rep = ccb_analysis_functions.checkrepviadoc(documentnum)
#     if rep == 0:
#         dismissalreasonsunrepold.append(reason)
#     elif rep == 1:
#         dismissalreasonsrepold.append(reason)
#     if secondreason != None:
#         reasonsfirstyear.append(secondreason)
#         if rep == 0:
#             dismissalreasonsunrepold.append(secondreason)
#         elif rep ==1:
#             dismissalreasonsrepold.append(secondreason)
# reasonseries = pd.Series(data=reasonsfirstyear)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsold', html_table)
# prevtable = soup.find(id="dismissalreasonsold")
# prevtable.replace_with(tablesoup)
# reasonseries = pd.Series(data=dismissalreasonsrepold)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsrepold', html_table)
# prevtable = soup.find(id="dismissalreasonsrepold")
# prevtable.replace_with(tablesoup)
# reasonseries = pd.Series(data=dismissalreasonsunrepold)
# df = reasonseries.value_counts().rename_axis('Reasons').reset_index(name='Orders')
# html_table = df.to_html(index=False, justify='center')
# tablesoup = ccb_analysis_functions.makeinserttable('dismissalreasonsunrepold', html_table)
# prevtable = soup.find(id="dismissalreasonsunrepold")
# prevtable.replace_with(tablesoup)

# Calculate time between claim and dimissal - mean, median, and mode
# For all dismissals, then past 30 days, by year of CCB
dismissalinfo = []
cur.execute('''SELECT DocketNumber, FilingDate FROM Documents WHERE 
            DocumentType LIKE "Order Dismissin%"''')
for row in cur:
    dismissalinfo.append([row[0], row[1]])
timestodis = []
timestodisrecent = []
timestodisold = []
timestodisyeartwo = []
timestodisyearthree = []
for dismissal in dismissalinfo:
    cur.execute('''SELECT FilingDate FROM Documents WHERE DocumentType = "Claim" AND 
                DocketNumber = ?''', (dismissal[0], ))
    claimdates = []
    for row in cur:
        claimdates.append(row[0])
    if len(claimdates) == 1:
        d1 = date.fromisoformat(claimdates[0])
        d2 = date.fromisoformat(dismissal[1])
        daysfromclaimtodismissal = (d2-d1).days
        timestodis.append(daysfromclaimtodismissal)
        if d2 > sixtydaysago:
            timestodisrecent.append(daysfromclaimtodismissal)
        if d2 < thirdanniversary and d2 >= secondanniversary:
            timestodisyearthree.append(daysfromclaimtodismissal)
        elif d2 < secondanniversary and d2 >= ccbanniversary:
            timestodisyeartwo.append(daysfromclaimtodismissal)
        elif d2 < ccbanniversary:
            timestodisold.append(daysfromclaimtodismissal)
    elif len(claimdates) > 1:
        print('Something weird is happening with calculating time to dismissal')
        print(dismissal, claimdates)
avgtimetodismissal = str(round(statistics.mean(timestodis)))
timetoinsert = ccb_analysis_functions.makeinsertspan('avgtodismissalall', avgtimetodismissal)
olddismissalspan = soup.find(id="avgtodismissalall")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmedian = str(round(statistics.median(timestodis)))
timetoinsert = ccb_analysis_functions.makeinsertspan('mediantodismissalall', dismissaltimesmedian)
olddismissalspan = soup.find(id="mediantodismissalall")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmode = str(statistics.multimode(timestodis))
timetoinsert = ccb_analysis_functions.makeinsertspan('modetodismissalall', dismissaltimesmode)
olddismissalspan = soup.find(id="modetodismissalall")
olddismissalspan.replace_with(timetoinsert)

avgtimetodismissal = str(round(statistics.mean(timestodisrecent)))
timetoinsert = ccb_analysis_functions.makeinsertspan('avgtodismissalrecent', avgtimetodismissal)
olddismissalspan = soup.find(id="avgtodismissalrecent")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmedian = str(round(statistics.median(timestodisrecent)))
timetoinsert = ccb_analysis_functions.makeinsertspan('mediantodismissalrecent', dismissaltimesmedian)
olddismissalspan = soup.find(id="mediantodismissalrecent")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmode = str(statistics.multimode(timestodisrecent))
timetoinsert = ccb_analysis_functions.makeinsertspan('modetodismissalrecent', dismissaltimesmode)
olddismissalspan = soup.find(id="modetodismissalrecent")
olddismissalspan.replace_with(timetoinsert)

avgtimetodismissal = str(round(statistics.mean(timestodisyearthree)))
timetoinsert = ccb_analysis_functions.makeinsertspan('avgtodismissalyearthree', avgtimetodismissal)
olddismissalspan = soup.find(id="avgtodismissalyearthree")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmedian = str(round(statistics.median(timestodisyearthree)))
timetoinsert = ccb_analysis_functions.makeinsertspan('mediantodismissalyearthree', dismissaltimesmedian)
olddismissalspan = soup.find(id="mediantodismissalyearthree")
olddismissalspan.replace_with(timetoinsert)
dismissaltimesmode = str(statistics.multimode(timestodisyearthree))
timetoinsert = ccb_analysis_functions.makeinsertspan('modetodismissalyearthree', dismissaltimesmode)
olddismissalspan = soup.find(id="modetodismissalyearthree")
olddismissalspan.replace_with(timetoinsert)

# Can stop running after 6/17/2024
# avgtimetodismissal = str(round(statistics.mean(timestodisyeartwo)))
# timetoinsert = ccb_analysis_functions.makeinsertspan('avgtodismissalyeartwo', avgtimetodismissal)
# olddismissalspan = soup.find(id="avgtodismissalyeartwo")
# olddismissalspan.replace_with(timetoinsert)
# dismissaltimesmedian = str(round(statistics.median(timestodisyeartwo)))
# timetoinsert = ccb_analysis_functions.makeinsertspan('mediantodismissalyeartwo', dismissaltimesmedian)
# olddismissalspan = soup.find(id="mediantodismissalyeartwo")
# olddismissalspan.replace_with(timetoinsert)
# dismissaltimesmode = str(statistics.multimode(timestodisyeartwo))
# timetoinsert = ccb_analysis_functions.makeinsertspan('modetodismissalyeartwo', dismissaltimesmode)
# olddismissalspan = soup.find(id="modetodismissalyeartwo")
# olddismissalspan.replace_with(timetoinsert)

# # Only needed to run once
# avgtimetodismissal = str(round(statistics.mean(timestodisold)))
# timetoinsert = ccb_analysis_functions.makeinsertspan('avgtodismissalold', avgtimetodismissal)
# olddismissalspan = soup.find(id="avgtodismissalold")
# olddismissalspan.replace_with(timetoinsert)
# dismissaltimesmedian = str(round(statistics.median(timestodisold)))
# timetoinsert = ccb_analysis_functions.makeinsertspan('mediantodismissalold', dismissaltimesmedian)
# olddismissalspan = soup.find(id="mediantodismissalold")
# olddismissalspan.replace_with(timetoinsert)
# dismissaltimesmode = str(statistics.multimode(timestodisold))
# timetoinsert = ccb_analysis_functions.makeinsertspan('modetodismissalold', dismissaltimesmode)
# olddismissalspan = soup.find(id="modetodismissalold")
# olddismissalspan.replace_with(timetoinsert)

#### All Cases
# Update number of cases
casecountspan = soup.find(id="allcasescount")
casecountspan.string.replace_with(str(len(allcases)))

#Update number closed
closedstatuses=[]
cur.execute('''SELECT Status, DocketNumber FROM Cases''')
for row in cur:
    status = row[0]
    if status is None:
        print('Status is None')
        print(row)
    elif (status.startswith('Final') or status.startswith('Dismiss') or 
        status.startswith('Closed')):
        closedstatuses.append(row[0])
closedcountspan = soup.find(id="numclosedcases")
closedcountspan.string.replace_with(str(len(closedstatuses)))
statusseries = pd.Series(data=closedstatuses)
df = statusseries.value_counts().rename_axis('Status').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
html_table.replace('border="1"', 'id="closedcasestatus"')
tablesoup = ccb_analysis_functions.makeinserttable('closedcasestatus', html_table)
statustable = soup.find(id="closedcasestatus")
statustable.replace_with(tablesoup)
#Number of final determinations updated earlier, with other span near beginning of page

# Update the chart about opening and closing cases
ends = (ccb_analysis_functions.last_dates_of_months(ccbstart, date.today()))
ends.add(date.today())
datestocheck = list(ends)
datestocheck.sort()
openandshut = []
docketswehave, dismissalswehave, fdswehave = set(), set(), set()
for item in datestocheck:
    monthbeingcounted = item.strftime("%b-%y")
    cur.execute('''SELECT DocketNumber from Documents WHERE FilingDate <= ?''', (item, ))
    for row in cur:
        docketnum = row[0]
        if docketnum not in docketswehave:
            openandshut.append((docketnum, 1, monthbeingcounted, 'New Dockets'))
            docketswehave.add(docketnum)
    cur.execute('''SELECT DocketNumber from Documents WHERE DocumentType LIKE "Order Dismissing Claim%" 
                AND FilingDate <= ?''', (item,))
    for row in cur:
        docketnum = row[0]
        if docketnum not in dismissalswehave:
            openandshut.append((docketnum, 1, monthbeingcounted, 'Dismissals'))
            dismissalswehave.add(docketnum)
    cur.execute('''SELECT DocumentNumber from Documents WHERE DocumentType LIKE "Final Determinatio%" 
                AND FilingDate <= ?''', (item,))
    for row in cur:
        documentnum = row[0]
        if documentnum not in fdswehave:
            openandshut.append((documentnum, 1, monthbeingcounted, 'Final Determinations'))
            fdswehave.add(documentnum)
df = pd.DataFrame(openandshut, columns =['Docket or Document', 'Number', 'Month', 'Type'])
fig = px.histogram(df, x="Month", y="Number",
             color='Type', barmode='group', 
             title="New dockets, dismissed claims, and final determinations by month")
fig.update_layout(barmode='group', bargap=0.05,bargroupgap=0.0)
fig.write_html("../bibliobaloney.github.io/charts/ccbopeningandclosing.html", include_plotlyjs='directory')

#Update types of claims for all available claims (not just open cases)
listclaimtypes = []
recentclaimtypes = []
yeartwoclaimtypes = []
yearthreeclaimtypes = []
oldclaimtypes = []
for case in allclaims:
    cur.execute('''SELECT InfringementYN, NoninfringementYN, DmcaYN FROM Cases WHERE DocketNumber = ?''', (case, ))
    for row in cur:
        claimtypes = []
        if row[0] == 1:
            claimtypes.append('Infringement')
        if row[1] == 1:
            claimtypes.append('Noninfringement')
        if row[2] == 1:
            claimtypes.append('DMCA Misrepresentation')
    stringofclaims = ', '.join(claimtypes)
    listclaimtypes.append(stringofclaims)
    cur.execute('''SELECT FilingDate FROM Documents WHERE DocketNumber = ? AND 
                    (DocumentType = "Claim" OR DocumentType = "Amended Claim")''', (case, ))
    if case in recentclaims:
        recentclaimtypes.append(stringofclaims)
    if case in thirdyearclaims:
        yearthreeclaimtypes.append(stringofclaims)
    elif case in secondyearclaims:
        yeartwoclaimtypes.append(stringofclaims)
    elif case in firstyearclaims:
        oldclaimtypes.append(stringofclaims)
allclaimstypes = pd.Series(data=listclaimtypes)
df = allclaimstypes.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
alltypestoinsert = ccb_analysis_functions.makeinserttable('allclaimtypes', html_table)
alltypes = soup.find(id="allclaimtypes")
alltypes.replace_with(alltypestoinsert)

claimtypesrecent = pd.Series(data=recentclaimtypes)
df = claimtypesrecent.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
typestoinsertrecent = ccb_analysis_functions.makeinserttable('recentclaimtypes', html_table)
recenttypes = soup.find(id="recentclaimtypes")
recenttypes.replace_with(typestoinsertrecent)

claimtypesyearthree = pd.Series(data=yearthreeclaimtypes)
df = claimtypesyearthree.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
typestoinsertyearthree = ccb_analysis_functions.makeinserttable('yearthreeclaimtypes', html_table)
yearthreetypes = soup.find(id="yearthreeclaimtypes")
yearthreetypes.replace_with(typestoinsertyearthree)

claimtypesyeartwo = pd.Series(data=yeartwoclaimtypes)
df = claimtypesyeartwo.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
typestoinsertyeartwo = ccb_analysis_functions.makeinserttable('yeartwoclaimtypes', html_table)
yeartwotypes = soup.find(id="yeartwoclaimtypes")
yeartwotypes.replace_with(typestoinsertyeartwo)

claimtypesold = pd.Series(data=oldclaimtypes)
df = claimtypesold.value_counts().rename_axis('Claim type').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
typestoinsertold = ccb_analysis_functions.makeinserttable('oldclaimtypes', html_table)
oldtypes = soup.find(id="oldclaimtypes")
oldtypes.replace_with(typestoinsertold)

# Update tables about whether claimants are choosing the smaller claims track
listsmaller = []
recentsmaller = []
yeartwosmaller = []
yearthreesmaller = []
oldsmaller = []
for case in allclaims:
    cur.execute('''SELECT SmallerYN FROM Cases WHERE DocketNumber = ?''', (case, ))
    for row in cur:
        smalleryn = 'No'
        if row[0] == 1:
             smalleryn = 'Yes'
    listsmaller.append(smalleryn)
    cur.execute('''SELECT FilingDate FROM Documents WHERE DocketNumber = ? AND 
                    (DocumentType = "Claim" OR DocumentType = "Amended Claim")''', (case, ))
    if case in recentclaims:
        recentsmaller.append(smalleryn)
    if case in thirdyearclaims:
        yearthreesmaller.append(smalleryn)
    elif case in secondyearclaims:
        yeartwosmaller.append(smalleryn)
    elif case in firstyearclaims:
        oldsmaller.append(smalleryn)
allsmaller = pd.Series(data=listsmaller)
df = allsmaller.value_counts().rename_axis('Smaller?').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
smallertoinsert = ccb_analysis_functions.makeinserttable('smallerall', html_table)
prevsmaller = soup.find(id="smallerall")
prevsmaller.replace_with(smallertoinsert)

smallerrecent = pd.Series(data=recentsmaller)
df = smallerrecent.value_counts().rename_axis('Smaller?').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
smallertoinsert = ccb_analysis_functions.makeinserttable('smallerrecent', html_table)
prevsmaller = soup.find(id="smallerrecent")
prevsmaller.replace_with(smallertoinsert)

smalleryearthree = pd.Series(data=yearthreesmaller)
df = smalleryearthree.value_counts().rename_axis('Smaller?').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
smallertoinsert = ccb_analysis_functions.makeinserttable('smalleryearthree', html_table)
prevsmaller = soup.find(id="smalleryearthree")
prevsmaller.replace_with(smallertoinsert)

# Year 2 data - no need to keep running
# smalleryeartwo = pd.Series(data=yeartwosmaller)
# df = smalleryeartwo.value_counts().rename_axis('Smaller?').reset_index(name='Cases')
# html_table = df.to_html(index=False, justify='center')
# smallertoinsert = ccb_analysis_functions.makeinserttable('smalleryeartwo', html_table)
# prevsmaller = soup.find(id="smalleryeartwo")
# prevsmaller.replace_with(smallertoinsert)

# # Year 1 data - no need to keep running
# smallerold = pd.Series(data=oldsmaller)
# df = smallerold.value_counts().rename_axis('Smaller?').reset_index(name='Cases')
# html_table = df.to_html(index=False, justify='center')
# smallertoinsert = ccb_analysis_functions.makeinserttable('smallerold', html_table)
# prevsmaller = soup.find(id="smallerold")
# prevsmaller.replace_with(smallertoinsert)

# Update representation information
# for all claims
representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(allclaims)
allrepaspercent = format((len(representedcases)/len(allclaims)), ".0%")
allmultiplefirms = str(caseswithmultiplefirms)
pctspans = soup.find_all(id="pctallclaimsrep")
for span in pctspans:
    span.string.replace_with(allrepaspercent)
allcasefirms = []
for item in allfirms:
    if item is None:
        allcasefirms.append('No law firm')
    else:
        allcasefirms.append(item)
allfirmsseries = pd.Series(data=allcasefirms)
dfwithsingles = allfirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
df = dfwithsingles[dfwithsingles['Cases'] > 1]
html_table = df.to_html(index=False, justify='center')
reptoinsert = ccb_analysis_functions.makeinserttable('representationall', html_table)
prevrep = soup.find(id="representationall")
prevrep.replace_with(reptoinsert)

# for recent claims
representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(recentclaims)
recentrepaspercent = format((len(representedcases)/len(recentclaims)), ".0%")
recentmultiplefirms = str(caseswithmultiplefirms)
oldspan = soup.find(id="pctrecentclaimsrep")
oldspan.string.replace_with(recentrepaspercent)
recentcasefirms = []
for item in allfirms:
    if item is None:
        recentcasefirms.append('No law firm')
    else:
        recentcasefirms.append(item)
recentfirmsseries = pd.Series(data=recentcasefirms)
df = recentfirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
html_table = df.to_html(index=False, justify='center')
reptoinsert = ccb_analysis_functions.makeinserttable('representationrecent', html_table)
prevrep = soup.find(id="representationrecent")
prevrep.replace_with(reptoinsert)

# for third year claims
representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(thirdyearclaims)
yearthreerepaspercent = format((len(representedcases)/len(thirdyearclaims)), ".0%")
yearthreemultiplefirms = str(caseswithmultiplefirms)
oldspan = soup.find(id="pctyearthreeclaimsrep")
oldspan.string.replace_with(yearthreerepaspercent)
yearthreecasefirms = []
for item in allfirms:
    if item is None:
        yearthreecasefirms.append('No law firm')
    else:
        yearthreecasefirms.append(item)
yearthreefirmsseries = pd.Series(data=yearthreecasefirms)
dfwithsingles = yearthreefirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
df = dfwithsingles[dfwithsingles['Cases'] > 1]
html_table = df.to_html(index=False, justify='center')
reptoinsert = ccb_analysis_functions.makeinserttable('representationyearthree', html_table)
prevrep = soup.find(id="representationyearthree")
prevrep.replace_with(reptoinsert)

# for second year claims
# Does not need to run every week
# representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(secondyearclaims)
# yeartworepaspercent = format((len(representedcases)/len(secondyearclaims)), ".0%")
# yeartwomultiplefirms = str(caseswithmultiplefirms)
# oldspan = soup.find(id="pctyeartwoclaimsrep")
# oldspan.string.replace_with(yeartworepaspercent)
# yeartwocasefirms = []
# for item in allfirms:
#     if item is None:
#         yeartwocasefirms.append('No law firm')
#     else:
#         yeartwocasefirms.append(item)
# yeartwofirmsseries = pd.Series(data=yeartwocasefirms)
# dfwithsingles = yeartwofirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
# df = dfwithsingles[dfwithsingles['Cases'] > 1]
# html_table = df.to_html(index=False, justify='center')
# reptoinsert = ccb_analysis_functions.makeinserttable('representationyeartwo', html_table)
# prevrep = soup.find(id="representationyeartwo")
# prevrep.replace_with(reptoinsert)

# for first year claims
## Does not need to run every week
# representedcases, caseswithmultiplefirms, allfirms = ccb_analysis_functions.checkrepresentation(firstyearclaims)
# oldrepaspercent = format((len(representedcases)/len(firstyearclaims)), ".0%")
# oldmultiplefirms = str(caseswithmultiplefirms)
# oldspan = soup.find(id="pctoldclaimsrep")
# oldspan.string.replace_with(oldrepaspercent)
# oldcasefirms = []
# for item in allfirms:
#     if item is None:
#         oldcasefirms.append('No law firm')
#     else:
#         oldcasefirms.append(item)
# oldfirmsseries = pd.Series(data=oldcasefirms)
# dfwithsingles = oldfirmsseries.value_counts().rename_axis('Law firm').reset_index(name='Cases')
# df = dfwithsingles[dfwithsingles['Cases'] > 1]
# html_table = df.to_html(index=False, justify='center')
# reptoinsert = ccb_analysis_functions.makeinserttable('representationold', html_table)
# prevrep = soup.find(id="representationold")
# prevrep.replace_with(reptoinsert)

### Works in infringement claims
#Collect all the data
worktypeall = []
worktyperecent = []
worktypeyeartwo = []
worktypeyearthree = []
worktypeold = []
registeredall = []
registeredrecent = []
registeredyeartwo = []
registeredyearthree = []
registeredold = []
cur.execute('''SELECT DocketNumber, WorkType, RegisteredYN from Works''')
for row in cur:
    docketnum = row[0]
    worktype = row[1]
    if row[2] == 1:
        registered = 'Yes'
    elif row[2] == 0:
        registered = 'No'
    worktypeall.append(worktype)
    registeredall.append(registered)
    if docketnum in recentclaims:
        worktyperecent.append(worktype)
        registeredrecent.append(registered)
    if docketnum in thirdyearclaims:
        worktypeyearthree.append(worktype)
        registeredyearthree.append(registered)
    elif docketnum in secondyearclaims:
        worktypeyeartwo.append(worktype)
        registeredyeartwo.append(registered)
    elif docketnum in firstyearclaims:
        worktypeold.append(worktype)
        registeredold.append(registered)

#Update all work types
series = pd.Series(data=worktypeall)
df = series.value_counts().rename_axis('Type of work').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('infringworktypesall', html_table)
prevtable = soup.find(id="infringworktypesall")
prevtable.replace_with(tabletoinsert)

#Update recent work types
series = pd.Series(data=worktyperecent)
df = series.value_counts().rename_axis('Type of work').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('infringworktypesrecent', html_table)
prevtable = soup.find(id="infringworktypesrecent")
prevtable.replace_with(tabletoinsert)

# Update work types from claims filed in the third year
series = pd.Series(data=worktypeyearthree)
df = series.value_counts().rename_axis('Type of work').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('infringworktypesyearthree', html_table)
prevtable = soup.find(id="infringworktypesyearthree")
prevtable.replace_with(tabletoinsert)

#Update work types from claims filed in the second year
# series = pd.Series(data=worktypeyeartwo)
# df = series.value_counts().rename_axis('Type of work').reset_index(name='Works')
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('infringworktypesyeartwo', html_table)
# prevtable = soup.find(id="infringworktypesyeartwo")
# prevtable.replace_with(tabletoinsert)

#Update work types from claims filed in the first year
# series = pd.Series(data=worktypeold)
# df = series.value_counts().rename_axis('Type of work').reset_index(name='Works')
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('infringworktypesold', html_table)
# prevtable = soup.find(id="infringworktypesold")
# prevtable.replace_with(tabletoinsert)

#Update all work registration info
series = pd.Series(data=registeredall)
df = series.value_counts().rename_axis('Registered?').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('registeredall', html_table)
prevtable = soup.find(id="registeredall")
prevtable.replace_with(tabletoinsert)

#Update registration info from recently filed claims
series = pd.Series(data=registeredrecent)
df = series.value_counts().rename_axis('Registered?').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('registeredrecent', html_table)
prevtable = soup.find(id="registeredrecent")
prevtable.replace_with(tabletoinsert)

#Update registration info from claims filed in the third year
series = pd.Series(data=registeredyearthree)
df = series.value_counts().rename_axis('Registered?').reset_index(name='Works')
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('registeredyearthree', html_table)
prevtable = soup.find(id="registeredyearthree")
prevtable.replace_with(tabletoinsert)

#Update registration info from claims filed in the second year
# series = pd.Series(data=registeredyeartwo)
# df = series.value_counts().rename_axis('Registered?').reset_index(name='Works')
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('registeredyeartwo', html_table)
# prevtable = soup.find(id="registeredyeartwo")
# prevtable.replace_with(tabletoinsert)

#Update registration info from claims filed in the first year
# series = pd.Series(data=registeredold)
# df = series.value_counts().rename_axis('Registered?').reset_index(name='Works')
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('registeredold', html_table)
# prevtable = soup.find(id="registeredold")
# prevtable.replace_with(tabletoinsert)

### Claimants
# Get list of claimants and update the table
cur.execute('''SELECT ClaimantName from Claimants''')
allclaimants = []
for row in cur:
    allclaimants.append(row[0])
claimants = pd.Series(data=allclaimants)
df = claimants.value_counts().rename_axis('Claimants').reset_index(name='Cases')
df = df[df['Cases'] > 2]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('claimantstable', html_table)
prevtable = soup.find(id='claimantstable')
prevtable.replace_with(tabletoinsert)

#Get a list of respondents and update the table
cur.execute('''SELECT RespondentName from Respondents''')
allrespondents = []
for row in cur:
    allrespondents.append(row[0])
respondents = pd.Series(data=allrespondents)
df = respondents.value_counts().rename_axis('Respondents').reset_index(name='Cases')
df = df[df['Cases'] > 2]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('respondentstable', html_table)
prevtable = soup.find(id='respondentstable')
prevtable.replace_with(tabletoinsert)

#Get a list of respondents that have opted out, update the table, csv, and count
cur.execute('''SELECT RespondentName from Respondents WHERE OptedOutYN = 1''')
alloptouts = []
for row in cur:
    alloptouts.append(row[0])
oldspan = soup.find(id="numoptouts")
oldspan.string.replace_with(str(len(alloptouts)))
optouts = pd.Series(data=alloptouts)
dfalloptouts = optouts.value_counts().rename_axis('Respondents opting out').reset_index(name='Cases')
dfalloptouts.to_csv('../bibliobaloney.github.io/allccboptouts.csv', index=False)
df = dfalloptouts[dfalloptouts['Cases'] > 1]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('optoutstable', html_table)
prevtable = soup.find(id='optoutstable')
prevtable.replace_with(tabletoinsert)

### Orders to Amend
#Create all 27 lists and sets - add 9 more for end of second year - 9 again for 3rd
allreasonsall, allreasonsrecent, allreasonsfirstyear = [], [], []
repreasonsall, repreasonsrecent, repreasonsfirstyear = [], [], []
unrepreasonsall, unrepreasonsrecent, unrepreasonsfirstyear = [], [], []
allreasonssecondyear, repreasonssecondyear, unrepreasonssecondyear = [], [], []
allreasonsthirdyear, repreasonsthirdyear, unrepreasonsthirdyear = [], [], []
numotasallall, numotasallrecent, numotasallfirstyear = set(), set(), set()
numotasrepall, numotasreprecent, numotasrepfirstyear = set(), set(), set()
numotasunrepall, numotasunreprecent, numotasunrepfirstyear = set(), set(), set()
numotasallsecondyear, numotasrepsecondyear, numotasunrepsecondyear = set(), set(), set()
numotasallthirdyear, numotasrepthirdyear, numotasunrepthirdyear = set(), set(), set()
allcasesall, allcasesrecent, allcasesfirstyear = set(), set(), set()
repcasesall, repcasesrecent, repcasesfirstyear = set(), set(), set()
unrepcasesall, unrepcasesrecent, unrepcasesfirstyear = set(), set(), set()
allcasessecondyear, repcasessecondyear, unrepcasessecondyear = set(), set(), set()
allcasesthirdyear, repcasesthirdyear, unrepcasesthirdyear = set(), set(), set()

cur.execute('''SELECT * FROM OrdersToAmend JOIN Documents USING(DocumentNumber)''')
for row in cur:
    reason = row[1]
    docketnum = row[2]
    documentnum = row[0]
    filingdate = date.fromisoformat(row[7])
    represented = ccb_analysis_functions.checkrepviacase(docketnum)
    allreasonsall.append(reason)
    numotasallall.add(documentnum)
    allcasesall.add(docketnum)
    if filingdate > sixtydaysago:
        allreasonsrecent.append(reason)
        numotasallrecent.add(documentnum)
        allcasesrecent.add(docketnum)
    if filingdate < thirdanniversary and filingdate >= secondanniversary:
        allreasonsthirdyear.append(reason)
        numotasallthirdyear.add(documentnum)
        allcasesthirdyear.add(docketnum)
    elif filingdate < secondanniversary and filingdate >= ccbanniversary:
        allreasonssecondyear.append(reason)
        numotasallsecondyear.add(documentnum)
        allcasessecondyear.add(docketnum)
    elif filingdate < ccbanniversary:
        allreasonsfirstyear.append(reason)
        numotasallfirstyear.add(documentnum)
        allcasesfirstyear.add(docketnum)
    if represented == 1:
        repreasonsall.append(reason)
        numotasrepall.add(documentnum)
        repcasesall.add(docketnum)
        if filingdate > sixtydaysago:
            repreasonsrecent.append(reason)
            numotasreprecent.add(documentnum)
            repcasesrecent.add(docketnum)
        if filingdate < thirdanniversary and filingdate >= secondanniversary:
            repreasonsthirdyear.append(reason)
            numotasrepthirdyear.add(documentnum)
            repcasesthirdyear.add(docketnum)
        elif filingdate < secondanniversary and filingdate >= ccbanniversary:
            repreasonssecondyear.append(reason)
            numotasrepsecondyear.add(documentnum)
            repcasessecondyear.add(docketnum)
        elif filingdate < ccbanniversary:
            repreasonsfirstyear.append(reason)
            numotasrepfirstyear.add(documentnum)
            repcasesfirstyear.add(docketnum)
    if represented == 0:
        unrepreasonsall.append(reason)
        numotasunrepall.add(documentnum)
        unrepcasesall.add(docketnum)
        if filingdate > sixtydaysago:
            unrepreasonsrecent.append(reason)
            numotasunreprecent.add(documentnum)
            unrepcasesrecent.add(docketnum)
        if filingdate < thirdanniversary and filingdate >= secondanniversary:
            unrepreasonsthirdyear.append(reason)
            numotasunrepthirdyear.add(documentnum)
            unrepcasesthirdyear.add(docketnum)
        if filingdate < secondanniversary and filingdate >= ccbanniversary:
            unrepreasonssecondyear.append(reason)
            numotasunrepsecondyear.add(documentnum)
            unrepcasessecondyear.add(docketnum)
        elif filingdate < ccbanniversary:
            unrepreasonsfirstyear.append(reason)
            numotasunrepfirstyear.add(documentnum)
            unrepcasesfirstyear.add(docketnum)

# all OTAS
series = pd.Series(data=allreasonsall)
reasonsfromallotasdf = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = reasonsfromallotasdf[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasallall', html_table)
prevtable = soup.find(id="otasallall")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numallreasonsall")
oldspan.string.replace_with(str(len(allreasonsall)))
oldspan = soup.find(id="numotasallall")
oldspan.string.replace_with(str(len(numotasallall)))
oldspan = soup.find(id="allcasesall")
oldspan.string.replace_with(str(len(allcasesall)))

# all OTAS from the past 60 days
series = pd.Series(data=allreasonsrecent)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasallrecent', html_table)
prevtable = soup.find(id="otasallrecent")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numallreasonsrecent")
oldspan.string.replace_with(str(len(allreasonsrecent)))
oldspan = soup.find(id="numotasallrecent")
oldspan.string.replace_with(str(len(numotasallrecent)))
oldspan = soup.find(id="allcasesrecent")
oldspan.string.replace_with(str(len(allcasesrecent)))

# all OTAS from the first year of the CCB
## Does not need to run every week
# series = pd.Series(data=allreasonsfirstyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasallfirstyear', html_table)
# prevtable = soup.find(id="otasallfirstyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numallreasonsold")
# oldspan.string.replace_with(str(len(allreasonsfirstyear)))
# oldspan = soup.find(id="numotasallold")
# oldspan.string.replace_with(str(len(numotasallfirstyear)))
# oldspan = soup.find(id="allcasesold")
# oldspan.string.replace_with(str(len(allcasesfirstyear)))

# all OTAS from cases with represented claimants
series = pd.Series(data=repreasonsall)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasrepall', html_table)
prevtable = soup.find(id="otasrepall")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numrepreasonsall")
oldspan.string.replace_with(str(len(repreasonsall)))
oldspan = soup.find(id="numotasrepall")
oldspan.string.replace_with(str(len(numotasrepall)))
oldspan = soup.find(id="repcasesall")
oldspan.string.replace_with(str(len(repcasesall)))

# represented claimant OTAS from the past 60 days
series = pd.Series(data=repreasonsrecent)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasreprecent', html_table)
prevtable = soup.find(id="otasreprecent")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numrepreasonsrecent")
oldspan.string.replace_with(str(len(repreasonsrecent)))
oldspan = soup.find(id="numotasreprecent")
oldspan.string.replace_with(str(len(numotasreprecent)))
oldspan = soup.find(id="repcasesrecent")
oldspan.string.replace_with(str(len(repcasesrecent)))

# represented claimant OTAS from the first year of the CCB
## Does not need to run every week
# series = pd.Series(data=repreasonsfirstyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasrepfirstyear', html_table)
# prevtable = soup.find(id="otasrepfirstyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numrepreasonsold")
# oldspan.string.replace_with(str(len(repreasonsfirstyear)))
# oldspan = soup.find(id="numotasrepold")
# oldspan.string.replace_with(str(len(numotasrepfirstyear)))
# oldspan = soup.find(id="repcasesold")
# oldspan.string.replace_with(str(len(repcasesfirstyear)))

# all OTAS from cases with unrepresented claimants
series = pd.Series(data=unrepreasonsall)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasunrepall', html_table)
prevtable = soup.find(id="otasunrepall")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numunrepreasonsall")
oldspan.string.replace_with(str(len(unrepreasonsall)))
oldspan = soup.find(id="numotasunrepall")
oldspan.string.replace_with(str(len(numotasunrepall)))
oldspan = soup.find(id="unrepcasesold")
oldspan.string.replace_with(str(len(unrepcasesall)))

# unrepresented claimant OTAS from the past 60 days
series = pd.Series(data=unrepreasonsrecent)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasunreprecent', html_table)
prevtable = soup.find(id="otasunreprecent")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numunrepreasonsrecent")
oldspan.string.replace_with(str(len(unrepreasonsrecent)))
oldspan = soup.find(id="numotasunreprecent")
oldspan.string.replace_with(str(len(numotasunreprecent)))
oldspan = soup.find(id="unrepcasesrecent")
oldspan.string.replace_with(str(len(unrepcasesrecent)))

# unrepresented claimant OTAS from the first year of the CCB
## Does not need to run every week
# series = pd.Series(data=unrepreasonsfirstyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasunrepfirstyear', html_table)
# prevtable = soup.find(id="otasunrepfirstyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numunrepreasonsold")
# oldspan.string.replace_with(str(len(unrepreasonsfirstyear)))
# oldspan = soup.find(id="numotasunrepold")
# oldspan.string.replace_with(str(len(numotasunrepfirstyear)))
# oldspan = soup.find(id="unrepcasesold")
# oldspan.string.replace_with(str(len(unrepcasesfirstyear)))

# all OTAS from the second year of the CCB
## Does not need to run every week
# series = pd.Series(data=allreasonssecondyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasallsecondyear', html_table)
# prevtable = soup.find(id="otasallsecondyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numallreasonsyeartwo")
# oldspan.string.replace_with(str(len(allreasonssecondyear)))
# oldspan = soup.find(id="numotasallyeartwo")
# oldspan.string.replace_with(str(len(numotasallsecondyear)))
# oldspan = soup.find(id="allcasesyeartwo")
# oldspan.string.replace_with(str(len(allcasessecondyear)))

# # represented claimant OTAS from the second year of the CCB
# ## Does not need to run every week
# series = pd.Series(data=repreasonssecondyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasrepsecondyear', html_table)
# prevtable = soup.find(id="otasrepsecondyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numrepreasonsyeartwo")
# oldspan.string.replace_with(str(len(repreasonssecondyear)))
# oldspan = soup.find(id="numotasrepyeartwo")
# oldspan.string.replace_with(str(len(numotasrepsecondyear)))
# oldspan = soup.find(id="repcasesyeartwo")
# oldspan.string.replace_with(str(len(repcasessecondyear)))

# # unrepresented claimant OTAS from the second year of the CCB
# ## Does not need to run every week
# series = pd.Series(data=unrepreasonssecondyear)
# df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
# df = df[:20]
# html_table = df.to_html(index=False, justify='center')
# tabletoinsert = ccb_analysis_functions.makeinserttable('otasunrepsecondyear', html_table)
# prevtable = soup.find(id="otasunrepsecondyear")
# prevtable.replace_with(tabletoinsert)
# oldspan = soup.find(id="numunrepreasonsyeartwo")
# oldspan.string.replace_with(str(len(unrepreasonssecondyear)))
# oldspan = soup.find(id="numotasunrepyeartwo")
# oldspan.string.replace_with(str(len(numotasunrepsecondyear)))
# oldspan = soup.find(id="unrepcasesyeartwo")
# oldspan.string.replace_with(str(len(unrepcasessecondyear)))

# all OTAS from the third year of the CCB
## Does not need to run every week
series = pd.Series(data=allreasonsthirdyear)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasallthirdyear', html_table)
prevtable = soup.find(id="otasallthirdyear")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numallreasonsyearthree")
oldspan.string.replace_with(str(len(allreasonsthirdyear)))
oldspan = soup.find(id="numotasallyearthree")
oldspan.string.replace_with(str(len(numotasallthirdyear)))
oldspan = soup.find(id="allcasesyearthree")
oldspan.string.replace_with(str(len(allcasesthirdyear)))

# represented claimant OTAS from the third year of the CCB
## Does not need to run every week
series = pd.Series(data=repreasonsthirdyear)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasrepthirdyear', html_table)
prevtable = soup.find(id="otasrepthirdyear")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numrepreasonsyearthree")
oldspan.string.replace_with(str(len(repreasonsthirdyear)))
oldspan = soup.find(id="numotasrepyearthree")
oldspan.string.replace_with(str(len(numotasrepthirdyear)))
oldspan = soup.find(id="repcasesyearthree")
oldspan.string.replace_with(str(len(repcasesthirdyear)))

# unrepresented claimant OTAS from the third year of the CCB
## Does not need to run every week
series = pd.Series(data=unrepreasonsthirdyear)
df = series.value_counts().rename_axis('Reason').reset_index(name='Orders')
df = df[:20]
html_table = df.to_html(index=False, justify='center')
tabletoinsert = ccb_analysis_functions.makeinserttable('otasunrepthirdyear', html_table)
prevtable = soup.find(id="otasunrepthirdyear")
prevtable.replace_with(tabletoinsert)
oldspan = soup.find(id="numunrepreasonsyearthree")
oldspan.string.replace_with(str(len(unrepreasonsthirdyear)))
oldspan = soup.find(id="numotasunrepyearthree")
oldspan.string.replace_with(str(len(numotasunrepthirdyear)))
oldspan = soup.find(id="unrepcasesyearthree")
oldspan.string.replace_with(str(len(unrepcasesthirdyear)))

reasonsfromallotasdf.to_csv('../bibliobaloney.github.io/allotareasons.csv')

print('Now updating the big "status over time" table; un-comment-out this section once a month (after the 16th)')
### Create the big crazy status chart
# First, get the list of dates to check on. 
statusdates = []
datetoadd = ccbstart + relativedelta(months=1)
while datetoadd < date.today():
    statusdates.append(datetoadd)
    datetoadd = datetoadd + relativedelta(months=1)
# Then start adding data points: for each date, count (open) cases matching a subset of statuses
listofstatustuples = []
for item in statusdates:
    statuses = []
    cases = set()
    cur.execute('''SELECT DocketNumber FROM Documents WHERE FilingDate < ?''', (item, ))
    for row in cur:
        cases.add(row[0])
    caselist = list(cases)
    for case in caselist:
        casestatus = ccbfunctions.getstatus(case, item)
        statuses.append(casestatus)
    statuscounts = {}
    for status in statuses:
        statuscounts[status] = statuscounts.get(status, 0) + 1
    openstatuses = ['In Abeyance', 'Waiting for Initial Review', 'Waiting for Amended Claim', 'Waiting for Review of Amended Claim', 
                    'Waiting for Proof of Service', 'Waiting for Scheduling Order/Expiration of Opt Out Window', 
                    'Active Phase']
    datestring = item.strftime("%y-%m-%d")
    for desc in statuscounts:
        if desc in openstatuses:
            listofstatustuples.append((datestring, desc, statuscounts[desc]))
df = pd.DataFrame(listofstatustuples, columns =['Date', 'Status', 'Count'])
fig=px.bar(df, x='Date', y='Count', color='Status', title="Number of open cases by status over time")
fig.write_html("../bibliobaloney.github.io/charts/ccbopencasesovertime.html", include_plotlyjs='directory')

cur.close()
conn.close()
with open("../bibliobaloney.github.io/index.html", "w", encoding='utf-8') as outf:
    outf.write(str(soup))
outf.close()
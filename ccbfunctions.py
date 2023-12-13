import re, requests, bs4
from datetime import date
from pdfminer.high_level import extract_text

# Return a tuple with 6 columns of info from a CCB doc search screen URL,
# plus a date that's a datetime object
def getpageofdocs(documentsurl):
    res = requests.get(documentsurl)
    res.raise_for_status()
    doclistsoup = bs4.BeautifulSoup(res.text, 'lxml')
    doclistrows = doclistsoup.find_all('tr')
    docsonthispage = []
    for row in doclistrows[1:]:
        cells = row.find_all('td')
        if len(cells) != 6:
            break
        docnumstr = cells[1].get_text(strip=True)
        documentnum = int(docnumstr.replace(',' , ''))
        docketnum = cells[0].get_text(strip=True)
        doctitle = cells[2].get_text(strip=True)
        doctitle = doctitle.removeprefix('Download')
        doctitle = doctitle.removeprefix('View')
        doctitle = doctitle.removesuffix('(Opens new window)')
        doctitle = doctitle.removesuffix('Toggle tooltip (Keyboard shortcut: "Crtl+Enter" opens and "Escape" or "Delete" dismiss)')
        doctype = cells[3].get_text(strip=True)
        docparty = cells[4].get_text(strip=True)
        datefiledstr = cells[5].get_text(strip=True)
        filingdate = date.fromisoformat(datefiledstr[6:10] + datefiledstr[:2] + datefiledstr[3:5])
        thisdoc = (documentnum, docketnum, doctitle, doctype, docparty, datefiledstr, filingdate)
        docsonthispage.append(thisdoc)
    return docsonthispage

# Return a docs tuple after you've already fetched the rows from a Beautiful Soup object
def getdocsfromrows(doclistrows):
    docsonthispage = []
    for row in doclistrows[1:]:
        cells = row.find_all('td')
        if len(cells) != 6:
            break
        docnumstr = cells[1].get_text(strip=True)
        documentnum = int(docnumstr.replace(',' , ''))
        docketnum = cells[0].get_text(strip=True)
        doctitle = cells[2].get_text(strip=True)
        doctitle = doctitle.removeprefix('Download')
        doctitle = doctitle.removeprefix('View')
        doctitle = doctitle.removesuffix('(Opens new window)')
        doctitle = doctitle.removesuffix('Toggle tooltip (Keyboard shortcut: "Crtl+Enter" opens and "Escape" or "Delete" dismiss)')
        doctype = cells[3].get_text(strip=True)
        docparty = cells[4].get_text(strip=True)
        datefiledstr = cells[5].get_text(strip=True)
        filingdate = date.fromisoformat(datefiledstr[6:10] + datefiledstr[:2] + datefiledstr[3:5])
        thisdoc = (documentnum, docketnum, doctitle, doctype, docparty, datefiledstr, filingdate)
        docsonthispage.append(thisdoc)
    return docsonthispage

#Gather information about types of claims and descriptions of disputes/relief. Returns an 9 item tuple
def claimtypesanddescriptions(soup):
    smallerdiv = soup.find(attrs={'data-field' : 'smallClaim'})
    smallerString = smallerdiv.get_text(strip=True)
    issmaller = 0
    if smallerString =='Yes':
        issmaller = 1
    typesdiv = soup.find(attrs={'data-field' : 'typeFlags'})
    stringoftypes = typesdiv.get_text(strip=True)
    isinfringement = 0
    infrdescription = 'Not applicable'
    if 'for infringement' in stringoftypes:
        isinfringement = 1
        infrdescriptionparentdiv = soup.find(attrs={'data-field' : 'description'})
        infrdescriptiondiv = infrdescriptionparentdiv.contents[1]
        infrdescription = infrdescriptiondiv.get_text(strip=True)
    isnoninfringement = 0
    noninfrdispute = 'Not applicable'
    if 'noninfringement' in stringoftypes:
        isnoninfringement = 1
        disputeparentdiv = soup.find(attrs={'data-field' : 'dispute'})
        disputediv = disputeparentdiv.contents[1]
        noninfrdispute = disputediv.get_text(strip=True)
    isdmca = 0
    explanofmisrep = 'Not applicapble'
    if '512' in stringoftypes:
        isdmca = 1
        misrepparentdiv = soup.find(attrs={'data-field' : 'explanationOfMisrepresentation'})
        misrepdiv = misrepparentdiv.contents[1]
        explanofmisrep = misrepdiv.get_text(strip=True)
    infringementrelief = 'Not applicable'
    dmcarelief = 'Not applicable'
    allreliefparentdivs = soup.find_all(attrs={'data-field' : 'harm'})
    if isinfringement == 1 and isdmca == 1:
        infringereliefparentdiv = allreliefparentdivs[0]
        infringementreliefdiv = infringereliefparentdiv.contents[1]
        infringementrelief = infringementreliefdiv.get_text(strip=True)
        dmcareliefparentdiv = allreliefparentdivs[1]
        dmcareliefdiv = dmcareliefparentdiv.contents[1]
        dmcarelief = dmcareliefdiv.get_text(strip=True)
    elif isinfringement == 1:
        reliefparentdiv = allreliefparentdivs[0]
        reliefdiv = reliefparentdiv.contents[1]
        infringementrelief = reliefdiv.get_text(strip=True)
    elif isdmca == 1:
        reliefparentdiv = allreliefparentdivs[0]
        reliefdiv = reliefparentdiv.contents[1]
        dmcarelief = reliefdiv.get_text(strip=True)
    return (issmaller, isinfringement, infrdescription, infringementrelief, isnoninfringement, noninfrdispute, isdmca,
            explanofmisrep, dmcarelief)

#List of states for comparing to claimant's partial address to see if they're in the US in getclaimantinfo
listofstates = (["AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO",
    "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR",
    "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY", "DC"])

#Get info about claimant(s) from claim page. Returns a list of tuples - one tuple per claimant
def getclaimantinfo(claimsoup):
    caseclaimants = []
    claimantinfodivs = claimsoup.find_all(id=re.compile("claimant"))
    for div in claimantinfodivs:
        claimantnameparentdiv = div.contents[1].contents[1].contents[1]
        claimantnamediv = claimantnameparentdiv.find(attrs={'data-field' : 'name'})
        claimantname = claimantnamediv.get_text(strip=True)
        claimantcityparentdiv = div.contents[1].contents[1]. contents[3]
        claimantcitydiv = claimantcityparentdiv.find(attrs={'data-field' : 'partialAddress'})
        if len(claimantcitydiv.find_all('br')) > 0:
            cityplusjunk = claimantcitydiv.contents
            claimantcity = cityplusjunk[0].get_text(strip=True) + ", " + cityplusjunk[2].get_text(strip=True)
        else:
            claimantcity = claimantcitydiv.get_text(strip=True)
        splitcity = claimantcity.split(",")
        claimantcityonly = splitcity[0]
        stateorcountry = splitcity[1][1:]
        claimantcountry = stateorcountry
        if stateorcountry in listofstates:
            claimantcountry = "USA"
        if claimsoup.find_all(string=re.compile('The representative is unknown.')):
            claimantrep = None
        else:
            claimantrepparentdiv = div.contents[1].contents[1].contents[7]
            claimantrepdiv = claimantrepparentdiv.find(attrs={'data-field' : 'name'})
            claimantrep = claimantrepdiv.get_text(strip=True)
        claimantlawfirm = None
        if claimsoup.find_all(string=re.compile('Law firm, clinic, or pro bono')):
            lawfirmhook = claimsoup.find(string=re.compile('Law firm'))
            lawfirmdiv = lawfirmhook.parent.parent.find(attrs={'data-field' : 'organization'})
            claimantlawfirm = lawfirmdiv.get_text(strip=True)
        caseclaimants.append((claimantname, claimantcityonly, stateorcountry, claimantcountry, claimantrep, claimantlawfirm))
    return caseclaimants

# Get info about respondents, and whether they've opted out. Returns a list of tuples
def checkrespondents(docketnum):
    respondentinfo = []
    partiesurl = 'https://dockets.ccb.gov/case/participants/' + docketnum
    res = requests.get(partiesurl)
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'lxml')
    respnamecells = soup.find_all(attrs={'headers' : 'colHeaderParty rowHeaderRESPONDENT'})
    if len(respnamecells) > 0:
        for respondent in respnamecells:
            respname = respondent.parent.contents[1].get_text(strip = True)
            resprep = respondent.parent.contents[3].get_text(strip = True)
            if len(resprep) == 0:
                resprep = None
            respfirm = respondent.parent.contents[5].get_text(strip = True)
            if len(respfirm) == 0:
                respfirm = None
            respondentinfo.append((respname, resprep, respfirm, 0))
    optoutnamecells = soup.find_all(attrs={'headers' : 'colHeaderOptOutParty rowHeaderOPT_OUT'})
    if len(optoutnamecells) > 0:
        for respondent in optoutnamecells:
            respname = respondent.parent.contents[1].get_text(strip = True)
            resprep = respondent.parent.contents[3].get_text(strip = True)
            if len(resprep) == 0:
                resprep = None
            respfirm = respondent.parent.contents[5].get_text(strip = True)
            if len(respfirm) == 0:
                respfirm = None
            respondentinfo.append((respname, resprep, respfirm, 1))
    return respondentinfo

#Get information about works described in an infringement claim. Returns list of tuples
def getworks(infringementclaimsoup):
    listofworks = []
    locators = infringementclaimsoup.find_all(attrs={"name" : re.compile("infringementData.workIds")})
    if len(locators) == 0:
        print("PROBLEM: no works found in this claim")
    workinfodivs = []
    for locator in locators:
        workinfodivs.append(locator.parent.contents[3].contents[1])
    for div in workinfodivs:
        title = div.contents[1].contents[3].get_text(strip=True)
        authors = div.contents[3].contents[3].get_text(strip=True)
        coowners = None
        if len(div.find_all(attrs={"data-field" : "coOwners"})) > 0:
            coowners = div.find(attrs={"data-field" : "coOwners"}).get_text(strip=True)
        reginfo = div.find(attrs={"data-field" : "registered"}).get_text(strip=True)
        registered = None
        if reginfo == 'Yes':
            registered = 1
        elif reginfo == 'No':
            registered = 0
        regnumber = None
        regdate = None
        if registered:
            regnumber = div.find(attrs={"data-field" : "registrationNumber"}).get_text(strip=True)
            regdatestr = div.find(attrs={"data-field" : "registrationEffectiveDate"}).get_text(strip=True)
            regdate = date.fromisoformat(regdatestr[6:] + regdatestr[:2] + regdatestr[3:5])
        requestnumber = None
        if registered == 0:
            requestnumber = div.find(attrs={"data-field" : "serviceRequestNumber"}).get_text(strip=True)
        worktype = div.find(attrs={"data-field" : "workType"}).get_text(strip=True)
        description = None
        if len(div.find_all(attrs={"data-field" : "workDescription"})) > 0:
            description = div.find(attrs={"data-field" : "workDescription"}).get_text(strip=True)
        listofworks.append((title, authors, coowners, registered, regnumber, regdate, requestnumber, worktype, description))
    return listofworks

#Given a document number, construct its URL and save the pdf locally in a folder called 'pdfs.' Returns nothing.
def getdocumentpdf(documentnum):
    documenturl = "https://dockets.ccb.gov/document/download/" + str(documentnum)
    res = requests.get(documenturl)
    res.raise_for_status()
    pdffile = open('pdfs/' + str(documentnum) + '.pdf', 'wb')
    for chunk in res.iter_content(100000):
        pdffile.write(chunk)
    pdffile.close()

#Given text, check whethr it includes "with prejudice," "without prejudice," or both. Returns integer.
def checkprejudice(pdftext):
    if "with prejudice" in pdftext and "without prejudice" in pdftext:
        return 2
    elif "without prejudice" in pdftext or "payment for your claim failed" in pdftext:
        return 0
    elif "with prejudice" in pdftext:
        return 1
    else:
        return None

#Given text, check it for various reasons a claim may be dismissed, and return a list.
def getdismissalreasons(pdftext):
    reasonsfound = []
    if 'FINDING OF BAD FAITH' in pdftext:
        reasonsfound.append("Bad-faith conduct")
    if 'No amended claim was filed in the time allowed' in pdftext or ('filed a Response to Amend' in pdftext and
                                                                       'past the deadline' in pdftext):
        reasonsfound.append("Failure to amend")
    if 'second amended claim' in pdftext and 'No amended claim was filed in the time allowed' not in pdftext:
        reasonsfound.append("3 tries and still noncompliant")
    if 'opt-out' in pdftext:
        reasonsfound.append("Respondent(s) opted out")
    if "did not receive  the respondent's address" in pdftext or "did not receive the respondent's address" in pdftext:
        reasonsfound.append("Failure to provide respondent address")
    if 'payment for the claim failed' in pdftext or 'payment for your claim failed' in pdftext:
        reasonsfound.append("Payment for the claim failed")
    if ('request from the claimant' in pdftext or 'request to dismiss from' in pdftext 
        or 'requested that it be withdrawn' in pdftext or 'submitted a request to have this claim dismissed' in pdftext or
        ('intended to request withdrawal of the claim' in pdftext 
         and 'received confirmation' in pdftext)):
        reasonsfound.append("Request from claimant")
    if ('did not file a proof of service or waiver of service' in pdftext or 'did not file a valid proof of service' in pdftext 
        or 'did not appear to reflect effective service' in pdftext):
        reasonsfound.append("Proof of service not filed")
    if 'Copyright Office refused' in pdftext or 'allegedly infringed work has been refused' in pdftext:
        reasonsfound.append("Copyright registration refused by Copyright Office")
    if 'not submit the second payment by' in pdftext:
        reasonsfound.append("Second filing fee not paid")
    if 'foreign invalid address' in pdftext and 'do not constitute bad faith' in pdftext:
        reasonsfound.append("Foreign respondent; no bad faith found")
    if ('request to re-open the case within 60 days of the Notice' in pdftext 
        or 'request to re-open the claim by January 26, 2024' in pdftext):
        reasonsfound.append("Settlement; will become dismissal with prejudice if claimant does not reopen in specified time")
    if 'grants the request, dismisses the claim with prejudice' in pdftext:
        reasonsfound.append("Settlement; dismissed with prejudice")
    if ('Settlement and Joint Request for Dismissal (without prejudice)' in pdftext
        or 'Settlement and Joint Request for Dismissal Without' in pdftext):
        reasonsfound.append("Settlement; dismissed without prejudice")
    if 'withdrawn the fee to register the allegedly infringed works' in pdftext:
        reasonsfound.append("Copyright registration application abandoned")
    if 'claimant did not validly serve' in pdftext or 'dismissed for failure to serve the respondent' in pdftext:
        reasonsfound.append("Service was not valid")
    return reasonsfound

# List of reasons for humandismissalinfo
reasonsmenu = {1: "Bad-faith conduct", 2: "Failure to amend", 3: "3 tries and still noncompliant", 4: "Respondent(s) opted out", 
               5: "Failure to provide respondent address", 6: "Payment for the claim failed", 7: "Request from claimant", 
               8: "Proof of service not filed", 9: "Copyright registration refused by Copyright Office", 
               10: "Second filing fee not paid", 11:"Foreign respondent; no bad faith found", 
               12: "Settlement; will become dismissal with prejudice if claimant does not reopen in specified time", 
               13: "Settlement; dismissed with prejudice", 14: "Settlement; dismissed without prejudice", 
               15: "Copyright registration application abandoned", 16: "Service was not valid", 17: None}

# Get a human to read the dismissal order. Returns tuple (HumanRead, WithPrejudice, SettlementMention, Reason1, Reason2)
def humandismissalinfo(documentnum, ordertext):
    print(ordertext)
    localfile = 'pdfs/' + str(documentnum) + '.pdf'
    documenturl = "https://dockets.ccb.gov/document/download/" + str(documentnum)
    print("PDF available at", localfile, "or", documenturl)
    prej = int(input('Enter 0 if dismissed without prejudice, 1 if with prejudice, 2 if conditional: '))
    settlement = int(input('Enter 1 if the order mentions a settlement, otherwise 0: '))
    for item in reasonsmenu:
        print(item, reasonsmenu[item])
    reasoninput1 = input('Enter a reason number from the menu: ')
    reason1 = reasonsmenu[int(reasoninput1)]
    reasoninput2 = input('Enter the second reason if there is one, 17 (None) if not: ')
    reason2 = reasonsmenu[int(reasoninput2)]
    dismissalinfo = (documentnum, 1, prej, settlement, reason1, reason2)
    return dismissalinfo
import sqlite3
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import BytesIO
import ccbfunctions

# Specify the PDF file you want to convert to HTML
pdf_file = '5850.pdf'

# Create an in-memory buffer to store the HTML output
output_buffer = BytesIO()

# Convert the PDF to HTML and write the HTML to the buffer
with open(pdf_file, 'rb') as pdf_file:
    extract_text_to_fp(pdf_file, output_buffer, output_type='html')

# Retrieve the HTML content from the buffer
html_content = output_buffer.getvalue().decode('utf-8')

# Specify the HTML file where you want to save the content
html_output_file = 'output.html'

# Save the HTML content to the HTML file
with open(html_output_file, 'w', encoding='utf-8') as html_file:
    html_file.write(html_content)

# try:
#     conn = sqlite3.connect("ccbdocstest.db")
#     cur = conn.cursor()
#     print("Successfully connected to ccbdocstest.db")
# except:
#     print("Error connecting to ccbdocstest.db")

# otas = []
# cur.execute('SELECT DocumentNumber from Documents WHERE DocumentType LIKE "Order to Amend%"')
# for row in cur:
#     otas.append(row[0])

# print(len(otas))

# for documentnum in otas[10:11]:
#     print(documentnum)
#     # ccbfunctions.getdocumentpdf(documentnum)
#     localfile = 'pdfs/' + str(documentnum) + '.pdf'
#     output_string = StringIO()
#     with open(localfile, 'rb') as fin:
#         extract_text_to_fp(fin, output_string, laparams=LAParams(), output_type='html', codec=None)
#     with open(converted_file, 'wb') as fout:
#         fout.write(output_string.getvalue())

# dismissalinfolist = []
# for documentnum in dismissals[100:150]:
#     print(documentnum)
#     # getdocumentpdf(documentnum)
#     localfile = 'pdfs/' + str(documentnum) + '.pdf'
#     ordertext = extract_text(localfile)
#     ordertext = ordertext.replace('\n', '')
#     ordertext = ordertext.replace('  ', ' ')
#     settlement = 0
#     if 'settlement' in ordertext:
#         settlement = 1
#     prej = ccbfunctions.checkprejudice(ordertext)
#     reasons = ccbfunctions.getdismissalreasons(ordertext)
#     if len(reasons) == 1 and (prej == 0 or prej ==1):
#         dismissalinfo = (documentnum, 0, prej, settlement, reasons[0], None)
#     else:
#         dismissalinfo = ccbfunctions.humandismissalinfo(documentnum, ordertext)
#     dismissalinfolist.append(dismissalinfo)

# for item in dismissalinfolist:
#     print(item)


# for documentnum in dismissals[:100]:
#     getdocumentpdf(documentnum)
#     localfile = 'pdfs/' + str(documentnum) + '.pdf'
#     ordertext = extract_text(localfile)
#     ordertext = ordertext.replace('\n', '')
#     ordertext = ordertext.replace('  ', ' ')
#     reasons = getdismissalreasons(ordertext)
#     prej = checkprejudice(ordertext)
    # if len(reasons) == 1 and (prej == 0 or prej == 1):
    #     print('okay')
    # else:
    #     print(documentnum)
    #     print(prej)
    #     print(reasons)
    #     print(ordertext)


# claimstotest = []
# cur.execute('SELECT DocketNumber, ClaimURL, FROM Cases WHERE InfringementYN = 1 ORDER BY DocketNumber')
# for row in cur:
#     claimstotest.append(row[1])
#     dateslist.append(row[2])

# for url in claimstotest[250:260]:
#     res = requests.get(url)
#     res.raise_for_status()
#     soup = bs4.BeautifulSoup(res.text, 'lxml')
#     print(getworks(soup))

# problemclaimants = ['https://dockets.ccb.gov/claim/view/1718', 'https://dockets.ccb.gov/claim/view/1905',
#                     'https://dockets.ccb.gov/claim/view/5118', 'https://dockets.ccb.gov/claim/view/290', 
#                     'https://dockets.ccb.gov/claim/view/3127', 'https://dockets.ccb.gov/claim/view/2015']

# respondentfishing = ['23-CCB-0324', '22-CCB-0071', '22-CCB-0015']

# listofstates = (["AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI",
#     "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO",
#     "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR",
#     "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY", "DC"])


# def getclaimantinfo(claimsoup):
#     caseclaimants = []
#     claimantinfodivs = claimsoup.find_all(id=re.compile("claimant"))
#     for div in claimantinfodivs:
#         claimantnameparentdiv = div.contents[1].contents[1].contents[1]
#         claimantnamediv = claimantnameparentdiv.find(attrs={'data-field' : 'name'})
#         claimantname = claimantnamediv.get_text(strip=True)
#         claimantcityparentdiv = div.contents[1].contents[1]. contents[3]
#         claimantcitydiv = claimantcityparentdiv.find(attrs={'data-field' : 'partialAddress'})
#         if len(claimantcitydiv.find_all('br')) > 0:
#             cityplusjunk = claimantcitydiv.contents
#             claimantcity = cityplusjunk[0].get_text(strip=True) + ", " + cityplusjunk[2].get_text(strip=True)
#         else:
#             claimantcity = claimantcitydiv.get_text(strip=True)
#         splitcity = claimantcity.split(",")
#         claimantcityonly = splitcity[0]
#         stateorcountry = splitcity[1][1:]
#         claimantcountry = stateorcountry
#         if stateorcountry in listofstates:
#             claimantcountry = "USA"
#         if claimsoup.find_all(string=re.compile('The representative is unknown.')):
#             claimantrep = None
#         else:
#             claimantrepparentdiv = div.contents[1].contents[1].contents[7]
#             claimantrepdiv = claimantrepparentdiv.find(attrs={'data-field' : 'name'})
#             claimantrep = claimantrepdiv.get_text(strip=True)
#         claimantlawfirm = None
#         if claimsoup.find_all(string=re.compile('Law firm, clinic, or pro bono')):
#             lawfirmhook = claimsoup.find(string=re.compile('Law firm'))
#             lawfirmdiv = lawfirmhook.parent.parent.find(attrs={'data-field' : 'organization'})
#             claimantlawfirm = lawfirmdiv.get_text(strip=True)
#         caseclaimants.append((claimantname, claimantcityonly, stateorcountry, claimantcountry, claimantrep, claimantlawfirm))
#     return caseclaimants

# for url in problemclaimants:
#     res = requests.get(url)
#     res.raise_for_status()
#     soup = bs4.BeautifulSoup(res.text, 'lxml')
#     print(url)
#     print(getclaimantinfo(soup))

# def isrepunknown(url):
#     res = requests.get(url)
#     res.raise_for_status()
#     soup = bs4.BeautifulSoup(res.text, 'lxml')
#     claimantinfodivs = soup.find_all(id=re.compile("claimant"))
#     for div in claimantinfodivs:
#         if div.find_all(string=re.compile('The representative is unknown.')):
#             return True
#     else:
#         return False
            
# repunknown = []
# cur.execute('SELECT DocketNumber, ClaimURL FROM Cases WHERE ClaimAvailableYN = 1')
# for row in cur:
#     docketnum = row[1]
#     url = row[1]
#     if isrepunknown(url):
#         repunknown.append([docketnum, url])

# print(repunknown)

#Claim2087 is multiple claimants and all 3 types of claims not smaller, 5804 is smaller,
#5800 is infringment only, 5407 DMCA only, 1227 noninfringement only
# testclaimurls = ['https://dockets.ccb.gov/claim/view/3087', 'https://dockets.ccb.gov/claim/view/5804', 
#                  'https://dockets.ccb.gov/claim/view/5800', 'https://dockets.ccb.gov/claim/view/5407', 
#                  'https://dockets.ccb.gov/claim/view/1227']

#5874 is represented claimant, 5800 and 5804 are single unrepresented, 3087 is 2 represented
# claimantfishing = ['https://dockets.ccb.gov/claim/view/5874', 'https://dockets.ccb.gov/claim/view/5800', 
#                    'https://dockets.ccb.gov/claim/view/3087', 'https://dockets.ccb.gov/claim/view/5804']

# res = requests.get('https://dockets.ccb.gov/claim/view/3087')
# res.raise_for_status()
# soup = bs4.BeautifulSoup(res.text, 'lxml')
# print(getreliefsought(soup))

# cur.execute("SELECT * from Cases WHERE (ClaimAvailableYN=0 AND Status IS NULL) OR (ClaimAvailableYN=0 AND Status!='Closed')")
# for row in cur:
#     print(row)

# docketswithinitialclaims = set()
# cur.execute('SELECT DocketNumber FROM Cases')
# for row in cur:
#     docketswithinitialclaims.add(row[0])

# noclaimavailableset = set()
# cur.execute('SELECT DocketNumber FROM Documents')
# for row in cur:
#     if row[0] not in docketswithinitialclaims:
#         noclaimavailableset.add(row[0])
# noclaimavailable = list(noclaimavailableset)
# noclaimavailable.sort()
# print(noclaimavailable)

# alldockets = set()
# cur.execute('SELECT DocketNumber FROM Documents')
# for row in cur:
#     alldockets.add(row[0])
# print(len(alldockets))

# amendedclaimrows = []
# cur.execute("SELECT DocumentNumber, DocketNumber FROM Documents WHERE DocumentType='Amended Claim' ORDER BY FilingDate")
# for row in cur:
#     print(row)

# rowsforcasestable = []
# cur.execute('SELECT DocumentNumber, DocketNumber FROM Documents WHERE DocumentType="Claim" ORDER BY DocketNumber')
# for row in cur:
#     docketnum = row[1]
#     claimurl = "https://dockets.ccb.gov/claim/view/" + str(row[0])
#     newclaim = (docketnum, 1, claimurl)
#     rowsforcasestable.append(newclaim)

# res = requests.get('https://dockets.ccb.gov/search/documents?max=100&offset=5800')
# res.raise_for_status()
# nodocsoup = bs4.BeautifulSoup(res.text, 'lxml')
# anyrows = nodocsoup.find_all('tr')
# print(len(anyrows))

# Check page w/ most recent documents & find out how many have been filed
# res = requests.get('https://dockets.ccb.gov/search/documents')
# res.raise_for_status()
# recentdoclistsoup = bs4.BeautifulSoup(res.text, 'lxml')
# topdocrow = recentdoclistsoup.find_all('tr')[1]
# topdoccells = topdocrow.find_all('td')
# topdocnumstr = topdoccells[1].get_text(strip=True)
# latestdocumentnum = int(topdocnumstr.replace(',' , ''))

# Use that number to determine how many batches of 100 to get
# if latestdocumentnum % 100 == 0:
#     pagestoget = latestdocumentnum/100
# else:
#     pagestoget = int(latestdocumentnum/100) + 1

#docsalreadyindb = []
#cur.execute('SELECT documentnum from Documents')
#for row in cur:
#    docsalreadyindb.append(row[0])
#print(docsalreadyindb)
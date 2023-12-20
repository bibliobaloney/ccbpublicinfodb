import sqlite3
import ccbfunctions

conn = sqlite3.connect("ccbdocstest.db")
cur = conn.cursor()
print("Successfully connected to ccbdocstest.db")

#In case you're running this for the first time or decided to restructure the OrdersToAmend table
otasrebuild = input('Do you want to (re)build the OrdersToAmend table from scratch (y/n)?')
if otasrebuild == 'y':
    cur.execute('DROP TABLE IF EXISTS OrdersToAmend')
    try:
        otas_table_query = '''CREATE TABLE OrdersToAmend (DocumentNumber INTEGER, Reason TEXT)'''
        cur.execute(otas_table_query)
        conn.commit()
        print("OrdersToAmend table freshly created")
    except sqlite3.Error as error:
        print("Possible error while creating OrdersToAmend table:", error)
else:
    print('Okay, skipping drop and rebuild OrdersToAmend')

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
                
counts = dict()
for reason in allthereasons:
    counts[reason] = counts.get(reason,0) + 1
reasonlist = []
for key, val in list(counts.items()):
    reasonlist.append((val, key))
reasonlist.sort(reverse=True)
for key, val in reasonlist:
    print(key, val)

print("New not-reasons:")
for order in notreasons:
    print(order)
    print(notreasons[order])

print('No reasons added in this many orders:', len(nothingfound))
print(nothingfound)

print("Adding info about Orders to Amend to database")
cur.executemany('''INSERT OR IGNORE INTO OrdersToAmend VALUES (?, ?)''', otainfolist)
conn.commit()
print("OTA info added for", cur.rowcount, "reasons")

print('Number of new Orders to Amend found at the beginning of this run:', len(newotas))

cur.close()

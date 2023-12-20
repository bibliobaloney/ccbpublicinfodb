import sqlite3
import pandas as pd
import plotly.express as px

conn = sqlite3.connect('ccbdocsinfo.db')
cur = conn.cursor()
allthereasons = []
cur.execute('''SELECT Reason1 FROM Dismissals''')
for row in cur:
    allthereasons.append(row[0])
cur.execute('''SELECT Reason2 FROM Dismissals''')
for row in cur:
    secondreason = row[0]
    if secondreason != None:
        allthereasons.append(secondreason)

reasonseries = pd.Series(data=allthereasons)
df = reasonseries.value_counts().rename_axis('reasons').reset_index(name='counts')
print(df)

fig = px.pie(df, values='counts', names='reasons')
fig.show()

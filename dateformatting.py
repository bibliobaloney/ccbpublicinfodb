from datetime import date

examples = ['10/31/2023 02:53 PM EST', '11/08/2023 12:06 PM EST', '11/08/2023 05:23 PM EDT']
converted = []

for ex in examples:
    newobj = date.fromisoformat(ex[6:10] + ex[:2] + ex[3:5])
    converted.append(newobj)

print(converted)
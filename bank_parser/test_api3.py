import requests

with open("test.csv", "w") as f:
    f.write("Some Title\nDate of Statement\n\nDate,Detail,Debit,Balance\n2026-05-13,Swiggy,250,500\n")

files = {'file': open('test.csv', 'rb')}
response = requests.post("http://localhost:8000/parse", files=files)
print(response.status_code)
print(response.text)

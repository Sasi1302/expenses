import requests

with open("test.csv", "w") as f:
    f.write("date,description,amount\n2026-05-13,Amazon,-120\n")

files = {'file': open('test.csv', 'rb')}
response = requests.post("http://localhost:8000/parse", files=files)
print(response.status_code)
print(response.text)

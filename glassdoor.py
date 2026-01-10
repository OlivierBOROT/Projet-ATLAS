import http.client

conn = http.client.HTTPSConnection("glassdoor-real-time.p.rapidapi.com")

headers = {
    "x-rapidapi-key": "a9967094a7mshf3fa1602fd12d1bp14efa8jsnb4f3d5fb7c41",
    "x-rapidapi-host": "glassdoor-real-time.p.rapidapi.com",
}

conn.request("GET", "/companies/search?query=Shape%20It", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))

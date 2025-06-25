import requests
import time

url=' https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis=341248,341248'
response=requests.get(url)
with open('check.txt','w') as f:
    f.write(response.text)
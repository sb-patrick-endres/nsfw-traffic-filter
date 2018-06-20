"""
I also need to set up the logic to make the second call with nextPageToken if total rows > 50000.
For now, it is slow and slightly manual on the combination of paginated returns from the GA Reporting API.
"""
import re
from pprint import pprint
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
import csv
import json

from apiclient.discovery import build
import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
CLIENT_SECRETS_PATH = 'client_secrets.json' 
VIEW_ID = '23399713'


def initialize_analyticsreporting():

  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=[tools.argparser])
  flags = parser.parse_args([])

  flow = client.flow_from_clientsecrets(
      CLIENT_SECRETS_PATH, scope=SCOPES,
      message=tools.message_if_missing(CLIENT_SECRETS_PATH))

  storage = file.Storage('analyticsreporting.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, flags)
  http = credentials.authorize(http=httplib2.Http())

  # Build the service object.
  analytics = build('analytics', 'v4', http=http, discoveryServiceUrl=DISCOVERY_URI)

  return analytics

def get_report(analytics):
  # Querying the report
  return analytics.reports().batchGet(
      body={
  "reportRequests": [
    {
      "viewId": "23399713",
      "dateRanges": [{"startDate": "2018-04-01", "endDate": "2018-04-09"}],
      "metrics": [{"expression": "ga:sessions"}],
      "dimensions": [{"name": "ga:landingPagePath"}],
      "dimensionFilterClauses": [{"filters": [{"dimensionName": "ga:medium", "operator": "EXACT","expressions": ["organic"]}]}],
      "pageSize": 5000,
    }
  ]
}
  ).execute()

  json_object = analytics.reports().batchGet(
          body={
      "reportRequests": [
        {
          "viewId": "23399713",
          "dateRanges": [{"startDate": "2018-06-01", "endDate": "2018-06-09"}],
          "metrics": [{"expression": "ga:sessions"}],
          "dimensions": [{"name": "ga:medium"},{"name": "ga:landingPagePath"}],
          "dimensionFilterClauses": [{"filters": [{"dimensionName": "ga:medium", "operator": "EXACT","expressions": ["organic"]}]}],
          "pageSize": 100,
        }
      ]
    }
      ).execute()
  print(json_object)
  with open('data.txt', 'w') as outfile:
    json.dump(json_object, outfile)

f = open('api_response.csv', 'wt', encoding='utf-8')

writer = csv.writer(f, lineterminator='\n')

# Initialize a list to use to import into Pandas
lp_list = []
sesh_list = []

def print_response(response):
  # Parses and writes to a CSV

  for report in response.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
    rows = report.get('data', {}).get('rows', [])

    for row in rows:
      dimensions = row.get('dimensions', [])
      dateRangeValues = row.get('metrics', [])
      drv2 = dateRangeValues[0].get("values")
      writer.writerow(dimensions + drv2)
      lp_list.append(str(dimensions))
      sesh_list.append(str(drv2))


def main():

  analytics = initialize_analyticsreporting()
  response = get_report(analytics)
  print_response(response)

if __name__ == '__main__':
  main()

f.close()

# Removing the additional text from the imported data
lp_list =[i[2:(len(i)-2)] for i in lp_list]

sesh_list =[i[2:(len(i)-2)] for i in sesh_list]

header_names = ['Landing Page', 'Sessions']

# Zip it and import it
ga_pandas = pd.DataFrame(list(zip(lp_list, sesh_list)), columns=header_names)

# Convert the sessions from an object to an integer
ga_pandas["Sessions"]= ga_pandas["Sessions"].astype(int)

# Check that everything went OK. 
print(ga_pandas.head())

print("This is GA Pandas .info()")
ga_pandas.info()

# creates the Trie class to transform the regex
class Trie():

    def __init__(self):
        self.data = {}

    def add(self, word):
        ref = self.data
        for char in word:
            ref[char] = char in ref and ref[char] or {}
            ref = ref[char]
        ref[''] = 1

    def dump(self):
        return self.data

    def quote(self, char):
        return re.escape(char)

    def _pattern(self, pData):
        data = pData
        if "" in data and len(data.keys()) == 1:
            return None

        alt = []
        cc = []
        q = 0
        for char in sorted(data.keys()):
            if isinstance(data[char], dict):
                try:
                    recurse = self._pattern(data[char])
                    alt.append(self.quote(char) + recurse)
                except:
                    cc.append(self.quote(char))
            else:
                q = 1
        cconly = not len(alt) > 0

        if len(cc) > 0:
            if len(cc) == 1:
                alt.append(cc[0])
            else:
                alt.append('[' + ''.join(cc) + ']')

        if len(alt) == 1:
            result = alt[0]
        else:
            result = "(?:" + "|".join(alt) + ")"

        if q:
            if cconly:
                result += "?"
            else:
                result = "(?:%s)?" % result
        return result

    def pattern(self):
        return self._pattern(self.dump())

# This file contains all the NSFW terms.
banned_words = [] 
with open('badword_list.txt') as wordbook:
    for word in wordbook:
        word.replace('\n', '')
        word = word.strip()
        word = word.replace(' ', '+')
        banned_words.append(word)
        pprint(word)

def trie_regex_from_words(words):
    trie = Trie()
    for word in words:
        trie.add(word)
    return trie.pattern()

regex_string = trie_regex_from_words(banned_words)

print(regex_string)

non_english = '|[^A-Za-z\\/\\+\\-0-9\\_\\&\\=\\s\\?\\.\\@\'\"\\(\\)\\:\\|]'

regex_string = regex_string + non_english

regex_match = re.compile(r'{}'.format(regex_string))

# confirms that things are working
print(regex_match)

ga_list = ga_pandas['Landing Page'].tolist()

nsfw_url_list = []

# creates the URL list to be filtered against the total sessions
for test_item in ga_list:
  test_item = test_item.replace('\\n', '')
  # removes the false negatives generated from the characters on the end of the /video/ URLs.
  if test_item.startswith('/video/'):
    test_item_2 = test_item[0:test_item.rfind('-')]
    test_value = re.search(regex_match, test_item_2)
    if test_value:
      nsfw_url_list.append(test_item)
  else:
    test_value = re.search(regex_match, test_item)
    if test_value:
      nsfw_url_list.append(test_item)

df_nsfw = pd.DataFrame(nsfw_url_list)

# Dumps all of the bad terms to a CSV to look through.
with open('bad_file_4.csv', 'w') as f:
    df_nsfw.to_csv(f, index=False, header=False)

bad_traffic = pd.DataFrame()

for index, row in ga_pandas.iterrows():
    if row['Landing Page'] in nsfw_url_list:
      bad_traffic = bad_traffic.append(row)

# If you want to make sure it is working, turn these on and you can manually check the columns.
# with open('test_1.csv', 'w') as f:
#     ga_pandas.to_csv(f, index=False)

# with open('test_2.csv', 'w') as f:
#     bad_traffic.to_csv(f, index=False)

# Initializing the plot and plots all traffic against NSFW traffic
fig = plt.figure()

ax = fig.add_subplot(111)

width = 0.4

ga_pandas[['Sessions']].sum().plot(kind='bar', color='blue', ax=ax, width=width, position = 1)

bad_traffic[['Sessions']].sum().plot(kind='bar', color='red', ax=ax, width=width, position=0)

plt.show()



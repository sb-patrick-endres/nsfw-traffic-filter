# This needs to be much more Pythonic and converted to functions to be used elsewhere. 
# This still needs to be hooked up to the GA Reporting API. Jesus, there is a ton of fucking work to be done here.
# Long term, this also needs to be converted to FlashText to improve the speed. 

import re
import pprint
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# This file contains all the NSFW terms.
file = open('badword_list.txt')

badword_list = list(file)

regex_string = ''

# transforms badword_list.txt into a regex
for word in badword_list:
	word.replace('\n', '')
	word = word.strip()
	word = word.replace('+', '\\+').replace('\\', '\\\\').replace('^', '\\^').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]').replace('.', '\\.').replace('|', '\\|')
	word = word.replace('?', '\\?').replace('*', '\\*').replace('(', '\\(').replace(')', '\\)')
	regex_item = f'.*?{word}.*?|'
	regex_string = regex_string + regex_item

# matches the URL structure of VB
regex_string = regex_string.replace(' ','+')

# required to pare the last | from the regex
regex_string = regex_string[:-1]

non_english = '|[^A-Za-z\\/\\+\\-0-9\\_\\&\\=\\s\\?\\.\\@\'\"\\(\\)\\:\\|]'

regex_string = regex_string + non_english

regex_match = re.compile(r'{}'.format(regex_string))

# confirms that things are working
print(regex_match)

# This is a list of routes from the file mentioned below. This will be converted to pull from the original Excel file
# This is an artifact from the previous incarnation of the script.
file = open('VB_May_1_to_May_31_routes.csv', encoding='UTF-8')

ga_list = list(file)

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

# creates the disavow file for the NSFW terms. I need a better naming convention for this.
# this should be generated dynamically, not how I am doing it now.
output = open('bad_file_4.csv', 'w', encoding='utf-8')

pprint.pprint(nsfw_url_list, output)

output.close()

data = pd.read_csv('bad_file_4.csv', index_col=None)

bad_word_list = data.iloc[:,0].tolist()

print(type(bad_word_list))

cleaned_list = []

for item in bad_word_list:
	item = item.strip()
	item = item.replace('[', '').replace(']', '')
	item = item.replace('\\n', '')
	item = item.replace("'", "")
	cleaned_list.append(item)

pprint.pprint(cleaned_list)

# This is the raw data for the month
df_one = pd.read_excel('VB_May_1_to_May_31.xlsx', 'Dataset1', index_col=None, na_values=['NA'])

df_two = df_one[['Landing Page', 'Sessions']]

# This becomes the list after we import the stuff from csv_reader_test.py.
# I need to fix this. This an artifact from the previous version of the script.
test_list = cleaned_list

# This becomes the NSFW data for the month
df_three = pd.DataFrame()

# generates the comparison file: the NSFW URL and the session count
for index, row in df_two.iterrows():
 	if row['Landing Page'] in test_list:
 		df_three = df_three.append(row)

# Everything up to plt.show() is just generating the plot with Anaconda.
fig = plt.figure()

ax = fig.add_subplot(111)

width = 0.4

df_two[['Sessions']].sum().plot(kind='bar', color='blue', ax=ax, width=width, position = 1)

df_three[['Sessions']].sum().plot(kind='bar', color='red', ax=ax, width=width, position=0)

plt.show()

# Still need to add in the output to Excel or output to CSV of the sums of the two DataFrames.
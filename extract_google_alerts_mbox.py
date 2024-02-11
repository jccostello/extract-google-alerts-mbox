"""
This script extracts content from an archive file that uses mbox format
and loads selected fields for eventual output to a CSV.
Each mbox message contains multiple articles.

Each row output will include email message date, email message id,
and fields extracted from a specific article in the email message.

You can run the program like this to read from MBOX_ARCHIVE and
output to FILENAME:

    python extract_google_alerts_mbox.py -m MBOX_ARCHIVE -o FILENAME

"""

import sys # Check version to avoid issues
if not sys.version_info > (2, 7):
    sys.exit("You need to use a version of Python 3 earlier than Python 3.12.")
elif not sys.version_info < (3, 12):
    sys.exit("Use Python 3.11 or earlier to avoid an issue with 3.12 and extruct.")

import os
import mailbox
import csv
import urllib.parse
from bs4 import BeautifulSoup
from email.utils import parsedate_tz
from extruct import MicrodataExtractor
import argparse

parser = argparse.ArgumentParser(
    description="Extract articles from a mailbox of Google Alerts to CSV.",
    epilog="The mbox file should be created using Google Takeout.")
parser.add_argument('-m', '--mbox', dest='mbox_file', 
                    required=True, help='Mailbox file (mbox format) to process')
parser.add_argument('-o', '--output', dest='output_file', required=True,
                    help='Where to output the extracts')
args = parser.parse_args()

# Variables
messages_parsed = []
messages_total = 0
messages_defective = 0
article_list = []

# Before trying to open it with mailbox.mbox(), verify that the mbox file 
# exists. If the file doesn't exist, mailbox.mbox() will try to create
# an empty file using the filename provided.
if not os.path.isfile(args.mbox_file):
    sys.exit("The mailbox file doesn't exist at the given location:", args.mbox_file)
if not os.access(args.mbox_file, os.R_OK):
    sys.exit("The mailbox file cannot be read:", args.mbox_file)

archive = mailbox.mbox(args.mbox_file)

# For each message, get headers (date, message id) and HTML content.
# Skip messages if there is a defect with some aspect of the message.
for key in archive.iterkeys():
    message = archive[key]
    messages_total = messages_total + 1

    if message.defects:
        print("Skipping message", key, "because of the following defects:", message.defects)
        messages_defective = messages_defective + 1
        continue    

    for step in message.walk():
        if 'html' in step.get_content_type():
            # Decode the payload twice, once from base64 by get_payload() and
            # again from the binary object that get_payload() returns.
            # Pass decode=True to get_payload() to decode the base64 content.
            # Use .decode() to decode this binary object as a string.
            html_content = step.get_payload(decode=True).decode('utf-8')

            # Parse the mailbox-friendly date into an 8-digit date value.
            date_tuple = parsedate_tz(message['date'])
            if date_tuple:
                date_mdcy = ''.join([str("{:0>2}").format(date_tuple[1]), 
                                    str("{:0>2}").format(date_tuple[2]), 
                                    str("{:0>2}").format(date_tuple[0])])
            else:
                print("Skipping message", key, "because the date couldn't be parsed:", message['date'])
                messages_defective = messages_defective + 1
                continue

            message_id = message['message-ID']
            
            # The message date and message ID will be added to the 
            # final output, while the html content will be parsed further
            # into individual articles for output.
            messages_parsed.append([date_mdcy, message_id, html_content])

print("Total messages in archive:", messages_total)
print("Total defective messages:", messages_defective)
print("Total messages with content successfully extracted:", len(messages_parsed))

try:
    archive.close
    print("Mailbox archive closed.")
except IOError:
    print("There was an error closing the mailbox archive.")

# From each entry in messages_parsed:
# - parse the entry's html content
# - find all articles within the html
# - clean bold tags before extruct.MicrodataExtractor does
# - extract each article's title, teaser, publisher, and url.
for entry in messages_parsed:
    soup = BeautifulSoup(entry[2], "html.parser")
    articles = soup.findAll("tr", {"itemtype": 'http://schema.org/Article'})
    for article in articles:
        # Before extracting data via MicrodataExtractor, remove <b> and </b>
        # tags to avoid breaking hyphenated words with extra spaces (and
        # avoid creating future problems for word tokenizing).
        # For example, MicrodataExtractor (using lxml.html.clean) transforms 
        #'<b>AI</b>-powered' into 'AI -powered' rather than 'AI-powered'.
        for bold_tag in article.find_all('b'):
            bold_tag.replace_with_children()
        article_text = str(article)

        # Extract article data into a dict.
        article_data = MicrodataExtractor().extract(article_text)
        
        # Trim Google's redirect code from the article URL.
        google_url = article_data[0]['properties']['url']
        parsed_url=urllib.parse.urlparse(google_url)
        url = urllib.parse.parse_qs(parsed_url.query).get('url', [''])[0]
        
        title = article_data[0]['properties']['name']
        teaser = article_data[0]['properties']['description']
        publisher = article_data[0]['properties']['publisher']['properties']['name']

        # The first field is the date from the parent email message.
        # The second field is the unique message id.
        article_list.append([entry[0], entry[1], url, title, publisher, teaser])

print("Extracted", len(article_list), 
      "Google Alert articles from the mailbox archive.")

# Export the article extracts to CSV
try:
    with open(args.output_file, 'w', newline='') as article_file:
        article_writer = csv.writer(article_file, delimiter='\t')
        article_writer.writerows(article_list)
        print("All Google Alert articles output.")
except IOError:
    print("Error while outputting articles to CSV file.")

exit()

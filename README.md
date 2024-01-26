
# extract_google_alerts_mbox.py

## Overview

This script extracts individual articles from each Google Alert email and
export the results to a tab-delimited file specified by you.

## Usage

python extract_google_alerts_mbox.py -m MBOX_ARCHIVE -o FILENAME

### Input file format

This script takes as input an archive file in mbox format containing Google
Alerts. I used [Google Takeout](https://takeout.google.com/) to export the alerts
from Gmail.

### About Google Alert emails

Google Alert emails contain summaries of and links to articles about a chosen
topic. The article entries provide potentially useful data, such as the URL
of the article reported by the Alert, as well as the article's title,
publisher, and teaser text.

### Output file format

The tab-delimited output contains the following columns:

* Message date
* Unique message-id
* Article URL
* Article title
* Article publisher
* Article teaser, often a summary of the article

## Background

I wrote this script to process four years of Google Alerts targeting a
specific topic. For this script to be useful to you, you can set up a
Google Alert for a topic of interest and let the alerts accumulate long
enough to create a substantial data set.

One possible use of the data is to tokenize words found in the title and
teaser fields, then map how word usage and phrase usage changes over time.

## Technical notes

### Data validation

The script performs minimal data validation, verifying only that the mbox
messages are not defective due to incomplete headers (as defined by
mailbox.mbox.defects) and that the date field is valid.

The script uses extruct.MicrodataExtractor to extract structured content
that has itemtype `http://schema.org/Article`.

### Cleaning bold tags using BeautifulSoup

**Short version:**

extruct.MicrodataExtractor replaces style tags with Unicode whitespace.

If you have text such as `<b>AI</b>-powered`, the cleaned
version will have an extra space: 'AI -powered'. That extra space adds
work to tokenizing hyphenated words.

**Longer version:**

extruct.MicrodataExtractor (using the underlying lxml.html.clean library)
replaces style tags with whitespace. There does not appear to be a way to
override this functionality.

Some of the content I extracted included style tags within hyphenated words.
When extruct.MicrodataExtractor cleans `<b>AI</b>-powered`, an extra space is
inserted before the hyphen, resulting in 'AI -powered'.

Since I want more control over how I tokenize hyphenated words, I added a step
before extraction to remove all bold tags. This did not significantly
increase the processing time for four years of alerts containing 10,000+
articles.

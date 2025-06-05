import csv
import time
import urllib.parse
import urllib.request
from datetime import datetime
import feedparser
import pandas as pd
from pathlib import Path
import re

version = "v2"  # version control variable

# Define updated query terms
model_terms = ['foundation model', 'foundation models', 'transformer', 'self-supervised']
signal_terms = ['wearable', 'biosignal']
health_terms = ['health', 'clinical', 'human activity recognition']
# Date cutoff
cutoff_date = datetime.strptime("2020-01-01", "%Y-%m-%d")

# Pagination settings
page_size = 200
base_url = "http://export.arxiv.org/api/query?"

# Helper function to escape LaTeX special characters in BibTeX fields
def latex_escape(text):
    replacements = {
        '\\': r'\\textbackslash{}',
        '{': r'\{',
        '}': r'\}',
        '$': r'\$',
        '&': r'\&',
        '%': r'\%',
        '#': r'\#',
        '_': r'\_',
        '^': r'\^{}',
        '~': r'\~{}',
        '"': "''"
    }
    regex = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    return regex.sub(lambda match: replacements[match.group()], text)

# Collect all results
results = []

# Run all combinations of model × signal × health terms
for model in model_terms:
    for signal in signal_terms:
        for health in health_terms:
            query = f'all:{model} AND all:{signal} AND all:{health}'
            encoded_query = urllib.parse.quote(query)
            start = 0
            print(f"🔍 Querying: {query}")

            while True:
                url = (
                    f"{base_url}search_query={encoded_query}"
                    f"&start={start}&max_results={page_size}&sortBy=lastUpdatedDate&sortOrder=descending"
                )
                print(f"   📄 Fetching results {start} to {start + page_size}...")
                try:
                    response = urllib.request.urlopen(url)
                    feed = feedparser.parse(response)
                except Exception as e:
                    print(f"   ❌ Request failed: {e}")
                    break

                if not feed.entries:
                    print("   ✅ No more entries.")
                    break

                count_this_page = 0
                for entry in feed.entries:
                    published = datetime.strptime(entry.published[:10], "%Y-%m-%d")
                    if published < cutoff_date:
                        continue

                    arxiv_id = entry.id.split('/')[-1]
                    title = entry.title.strip().replace('\n', ' ')
                    authors = ", ".join(author.name for author in entry.authors)
                    abstract = entry.summary.replace('\n', ' ').strip()
                    pdf_link = entry.id.replace('abs', 'pdf')

                    results.append({
                        "arXiv ID": arxiv_id,
                        "Title": title,
                        "Authors": authors,
                        "Published": published.strftime("%Y-%m-%d"),
                        "Abstract": abstract,
                        "PDF Link": pdf_link
                    })

                    count_this_page += 1

                if count_this_page == 0:
                    print("   🚫 No new results. Ending.")
                    break

                start += page_size
                time.sleep(1)

# Deduplicate after collection
df = pd.DataFrame(results)
df = df.drop_duplicates(subset="arXiv ID")

# Save as BibTeX with abstracts
if not df.empty:
    bib_entries = []
    for _, row in df.iterrows():
        bib_id = row["arXiv ID"].replace('.', '').replace('/', '')
        authors_bib = " and ".join(row["Authors"].split(", "))
        year = row["Published"][:4]
        title_escaped = latex_escape(row["Title"])
        abstract_escaped = latex_escape(row["Abstract"])

        bib_entry = f"""@article{{{bib_id},
  title={{ {title_escaped} }},
  author={{ {authors_bib} }},
  journal={{ arXiv preprint arXiv:{row["arXiv ID"]} }},
  year={{ {year} }},
  url={{ {row["PDF Link"].replace('.pdf', '')} }},
  abstract={{ {abstract_escaped} }}
}}"""
        bib_entries.append(bib_entry)

    output_path = f"arxiv_foundation_model_results_{version}.bib"
    Path(output_path).write_text("\n\n".join(bib_entries), encoding="utf-8")
    print(f"\n✅ Saved {len(df)} BibTeX entries with abstracts to {output_path}")
else:
    print("\n❌ No matching papers found.")
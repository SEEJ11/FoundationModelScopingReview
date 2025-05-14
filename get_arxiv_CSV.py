
import csv
import time
import urllib.parse
import urllib.request
from datetime import datetime
import feedparser
import pandas as pd

# Define the updated query terms
model_terms = ['foundation model', 'foundation models', 'transformer', 'self-supervised']
signal_terms = ['wearable', 'biosignal']
health_terms = ['health', 'clinical', 'human activity recognition']

# Date cutoff
cutoff_date = datetime.strptime("2020-01-01", "%Y-%m-%d")

# Pagination settings
page_size = 200
base_url = "http://export.arxiv.org/api/query?"

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

# Save to CSV
if not df.empty:
    filename = "arxiv_combined_deduplicated_results.csv"
    df.to_csv(filename, index=False)
    print(f"\n✅ Done. Saved {len(df)} deduplicated papers to {filename}")
else:
    print("\n❌ No matching papers found.")

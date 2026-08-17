import requests
import json

def get_metadata(title):
    url = "https://api.crossref.org/works"
    params = {
        "query.title": title,
        "rows": 10
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        
        for item in items:
            item_titles = item.get("title", [])
            if not item_titles: continue
            item_title = item_titles[0]
            
            # Use a slightly more flexible match but expect high similarity
            if title.lower().replace(" ", "") in item_title.lower().replace(" ", "") or \
               item_title.lower().replace(" ", "") in title.lower().replace(" ", ""):
                
                doi = item.get("DOI", "")
                journals = item.get("container-title", [])
                journal = journals[0] if journals else ""
                volume = item.get("volume", "")
                issue = item.get("issue", "")
                pages = item.get("page", "")
                
                year = None
                for field in ["published-print", "published-online", "issued", "created"]:
                    dp = item.get(field, {}).get("date-parts", [])
                    if dp and dp[0] and dp[0][0]:
                        year = dp[0][0]
                        break
                
                authors_list = item.get("author", [])
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list]
                full_author_str = " and ".join(authors)
                
                data = {
                    "title": item_title,
                    "journal": journal,
                    "year": year,
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "doi": doi,
                    "authors": authors
                }
                
                print(f"MATCH FOUND FOR: {title}")
                print("JSON:")
                print(json.dumps(data, indent=2))
                print("\nBibTeX-like:")
                print(f"  title = {{{item_title}}},")
                print(f"  journal = {{{journal}}},")
                print(f"  year = {{{year}}},")
                if volume: print(f"  volume = {{{volume}}},")
                if issue: print(f"  number = {{{issue}}},")
                if pages: print(f"  pages = {{{pages}}},")
                print(f"  doi = {{{doi}}},")
                print(f"  author = {{{full_author_str}}}")
                print("-" * 60)
                return True
        print(f"No exact match found for: {title}")
        return False
    except Exception as e:
        print(f"Error searching for '{title}': {e}")
        return False

titles = [
    "Markov Model-Driven in Real-time Faulty Node Detection for Naval Distributed Control Networked Systems",
    "An Intra-Wireless Vessel Communications Using Analysis of Interference Probability between Radio Devices"
]

for t in titles:
    get_metadata(t)

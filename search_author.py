import requests
import json
import re

def search_author_works(author_name):
    url = "https://api.crossref.org/works"
    params = {
        "query.author": author_name,
        "rows": 200  # Get more to filter thoroughly
    }
    
    keywords = ["maritime", "naval", "vessel", "wireless", "routing", "fault", "resilient", "industrial", "iot"]
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        
        valid_works = []
        
        for item in items:
            authors = item.get("author", [])
            # Filter for Dong-Seong Kim or Dong Seong Kim
            has_author = False
            for a in authors:
                given = a.get("given", "").lower()
                family = a.get("family", "").lower()
                if family == "kim" and ("dong-seong" in given or "dong seong" in given):
                    has_author = True
                    break
            
            if not has_author:
                continue
            
            title = item.get("title", [""])[0]
            venue = item.get("container-title", [""])[0]
            doi = item.get("DOI", "")
            
            year = None
            for field in ["published-print", "published-online", "issued"]:
                dp = item.get(field, {}).get("date-parts", [])
                if dp and dp[0] and dp[0][0]:
                    year = dp[0][0]
                    break
            
            author_names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]
            
            # Score based on keywords
            score = 0
            text_to_search = (title + " " + venue).lower()
            for kw in keywords:
                if kw in text_to_search:
                    score += 1
            
            valid_works.append({
                "title": title,
                "year": year,
                "venue": venue,
                "doi": doi,
                "authors": author_names,
                "score": score
            })
            
            if len(valid_works) >= 50: # Sufficient pool
                break

        # Print top 20 found (unsorted or initially filtered)
        print(f"Found {len(valid_works)} works matching author criteria. Top 20 relevant-ish:")
        for i, work in enumerate(valid_works[:20]):
            print(f"{i+1}. {work['title']} ({work['year']}) - {work['venue']}")
            print(f"   DOI: {work['doi']}")
            print(f"   Authors: {', '.join(work['authors'][:5])}...")
            print("-" * 20)
            
        # Select best 5
        best_5 = sorted(valid_works, key=lambda x: x['score'], reverse=True)[:5]
        
        print("\n" + "="*30)
        print("BEST 5 CANDIDATES BASED ON KEYWORDS")
        print("="*30)
        for i, work in enumerate(best_5):
            print(f"Rank {i+1} (Score: {work['score']}):")
            print(f"Title: {work['title']}")
            print(f"Year: {work['year']}")
            print(f"Venue: {work['venue']}")
            print(f"DOI: https://doi.org/{work['doi']}")
            print(f"Authors: {', '.join(work['authors'])}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")

search_author_works("Dong-Seong Kim")

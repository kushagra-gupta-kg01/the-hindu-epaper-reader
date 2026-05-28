import json

def main():
    with open("delhi_cciobjects.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print("=== Pages in Today's Delhi Edition ===")
    pages = data.get("children", [])
    
    for i, page in enumerate(pages):
        page_id = page.get("id")
        page_name = page.get("attributes", {}).get("Name", "Unnamed Page")
        page_number = page.get("attributes", {}).get("Page", "N/A")
        sub_children = page.get("children", [])
        
        # Count sub-children by kind
        kinds = {}
        articles = []
        for c in sub_children:
            kind = c.get("kind")
            kinds[kind] = kinds.get(kind, 0) + 1
            if kind == "Article":
                articles.append(c)
                
        print(f"Page {page_number}: {page_name} | Sub-elements: {kinds}")
        
        # Show first 2 articles on this page if any
        if articles:
            print("  Articles on this page:")
            for art in articles[:3]:
                art_name = art.get("attributes", {}).get("Name", "Unnamed Article")
                art_id = art.get("id")
                art_head = art.get("attributes", {}).get("Headline", "")
                
                # Check contents of the article
                contents = art.get("content", [])
                refs = [c.get("reference") for c in contents if c.get("reference")]
                
                # Check child elements of the article
                art_children = art.get("children", [])
                art_child_kinds = [ac.get("kind") for ac in art_children]
                
                print(f"    - [{art_id}] Name: {art_name} | Headline: {art_head}")
                print(f"      Content Refs: {refs}")
                print(f"      Sub-elements: {art_child_kinds}")
                
                # Let's inspect sub-elements of the article if there are any Text elements
                for sc in art_children:
                    if sc.get("kind") == "Text":
                        sc_contents = sc.get("content", [])
                        sc_refs = [scc.get("reference") for scc in sc_contents if scc.get("reference")]
                        print(f"        * Text element {sc.get('id')} has references: {sc_refs}")
            print()

if __name__ == "__main__":
    main()

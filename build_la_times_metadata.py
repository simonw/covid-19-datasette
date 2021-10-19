import httpx
from bs4 import BeautifulSoup as Soup
import json


def render_markdown(markdown):
    return httpx.post(
        "https://api.github.com/markdown", json={"mode": "markdown", "text": markdown}
    ).text


def extract_table_metadata(html):
    soup = Soup(html, "html5lib")
    table_metadata = {}
    for table in soup.findAll("table"):
        h4 = table.find_previous("h4")
        table_name = h4.text.strip()
        if not table_name.endswith(".csv"):
            continue
        table_name = table_name.replace(".csv", "")
        # Collect all HTML up to the <table> tag
        fragments = []
        for sibling in h4.next_siblings:
            fragment = str(sibling).strip()
            if "<table>" in fragment:
                break
            elif fragment:
                fragments.append(fragment)
        description_html = "\n".join(fragments)
        # Collect column metadata from the table
        columns = dict(
            [
                (tr.find("td").text, tr.findAll("td")[2].text)
                for tr in table.find("tbody").findAll("tr")
            ]
        )
        table_metadata[table_name] = {
            "description_html": description_html,
            "columns": columns,
        }
    return table_metadata


if __name__ == "__main__":
    markdown = open("california-coronavirus-data/README.md").read()
    html = render_markdown(markdown)
    table_metadata = extract_table_metadata(html)
    # Rewrite the metadata.json file
    metadata = json.load(open("metadata.json"))
    metadata["databases"]["la-times"] = {"tables": table_metadata}
    # Add source/license/about to each table
    for table_name in table_metadata:
        table_metadata[table_name].update(
            {
                "source": "LA Times California coronavirus data",
                "source_url": "https://github.com/datadesk/california-coronavirus-data",
                "about": "README",
                "about_url": "https://github.com/datadesk/california-coronavirus-data/blob/master/README.md#{}csv".format(
                    table_name
                ),
                "license": "Reusing the data",
                "license_url": "https://github.com/datadesk/california-coronavirus-data/blob/master/README.md#reusing-the-data",
            }
        )
    open("metadata.json", "w").write(json.dumps(metadata, indent=4))

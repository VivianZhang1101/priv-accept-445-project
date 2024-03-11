import json
import pandas as pd
from urllib.parse import urlparse
import os
import sys


def extract_domain(url):
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            return parsed_url.netloc
        else:
            return None
    except Exception:
        return None

def parse_file(filename):
    f = open(filename, 'r')
    data = json.load(f)
    
    # parsing cookies data
    cookie_first = [{"domain": cookie['domain'], "expires": cookie['expires'],
                     "size": cookie['size'], "name": cookie['name']} for cookie in data['first']['cookies']['cookies']]
    cookie_click = [{"domain": cookie['domain'], "expires": cookie['expires'],
                           "size": cookie['size'], "name": cookie['name']} for cookie in data['second']['cookies']['cookies']] #  use 'second' or 'click'?
    
    if data['internal'] is not None:
        cookie_internal = [{"domain": cookie['domain'], "expires": cookie['expires'],
                                  "size": cookie['size'], "name": cookie['name']} for cookie in data['internal']['cookies']['cookies']]
    else:
        cookie_internal = []

    # parsing domains
    domains_first = list(set({extract_domain(
        url) for url in data['first']['urls'] if extract_domain(url) is not None}))
    domains_click = list(set({extract_domain(
        url) for url in data['second']['urls'] if extract_domain(url) is not None}))
    
    new_row = {
    "url": data['stats']['target'],
    "landing_page": data['stats']['after-click-landing-page'],
    "has_found_banner": data['stats']['has-found-banner'],
    "cookie_first": json.dumps(cookie_first),
    "cookie_click": json.dumps(cookie_click),
    "cookie_internal": json.dumps(cookie_internal),
    "domains_first": json.dumps(domains_first),
    "domains_click": json.dumps(domains_click)
}
    return new_row
    # Append the new row to the DataFrame
    # new_df = pd.DataFrame([new_row])
    # df = pd.concat([df, new_df], ignore_index=True)

def read_files_in_folder(output_folder_path):
    if not os.path.isdir(output_folder_path):
        print("The provided path is not a valid directory.")
        return
    # df = pd.DataFrame(columns=['url', 'landing_page', 'has_found_banner',
    #                   'cookie_first', 'cookie_click', 'cookie_internal','domains_first','domains_click'])
    data = []
    for filename in os.listdir(output_folder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(output_folder_path, filename)
            if os.path.isfile(file_path):
                parse_row = parse_file(file_path)
                data.append(parse_row)

    return pd.DataFrame(data)

    


def main():
    if len(sys.argv) != 3:
        print("Usage: python parse.py <output_folder_path> <output_file_name>")
        # exampel: python parse.py data/USA/US data/USA_output.csv
        sys.exit(1)
    output_folder_path = sys.argv[1]
    output_file_name = sys.argv[2]
    df = read_files_in_folder(output_folder_path)
    if not df.empty:
        if os.path.exists(output_file_name):
            # Delete the existing file
            os.remove(output_file_name)
        df.to_csv(output_file_name, index=False)
        print(f"Data exported to {output_file_name}")
    
if __name__ == '__main__':
    main()

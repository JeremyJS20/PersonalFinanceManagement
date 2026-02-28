import urllib.request
import sys

def download_html(url, output_path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        print(f"Successfully downloaded {url} to {output_path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fetch_stitch.py <url> <output_path>")
    else:
        download_html(sys.argv[1], sys.argv[2])

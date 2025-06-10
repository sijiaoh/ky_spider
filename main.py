from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=SH605136&color=b#/cwfx"

def grab_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        html = page.content()
        browser.close()
    return html

def main():
    html = grab_html(URL)

    soup = BeautifulSoup(html, "lxml")

    title = soup.select_one("title").text.strip()
    headings = [h.text.strip() for h in soup.select("h2")]

    print(soup.prettify())
    print("TITLE:", title)
    print("H2s :", headings)

if __name__ == "__main__":
    main()

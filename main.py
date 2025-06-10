from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=SH605136&color=b#/cwfx"

def grab_htmls(urls):
    htmls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for url in urls:
            page.goto(url)
            htmls.append(page.content())
        browser.close()
    return htmls

def main():
    html = grab_htmls([URL])[0]

    soup = BeautifulSoup(html, "lxml")

    title = soup.select_one("title").text.strip()
    headings = [h.text.strip() for h in soup.select("h2")]

    print("TITLE:", title)
    print("H2s :", headings)

if __name__ == "__main__":
    main()

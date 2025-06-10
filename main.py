from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
from io import StringIO

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
    print("TITLE:", title)

    zyzb_table = soup.select_one(".zyzb_table .report_table .table1")
    df = pd.read_html(StringIO(str(zyzb_table)))[0]
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()

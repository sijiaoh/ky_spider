from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
from io import StringIO

URL = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=SH605136&color=b#/cwfx"

def grab_htmls(urls):
    htmls = {}
    for url in urls:
        htmls[url] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in urls:
            while True:
                page.goto(url)
                htmls[url].append(page.content())

                button = page.query_selector(".zyzb_table .next")
                if button is None or not button.is_visible():
                    break

                table_html = page.query_selector(".zyzb_table").inner_html()
                button.click()
                page.wait_for_function(
                    """
                        (oldHtml) => {
                            const newHtml = document.querySelector(".zyzb_table").innerHTML;
                            return oldHtml !== newHtml;
                        }
                    """,
                    arg=table_html,
                    timeout=1000
                )

        browser.close()

    return htmls

def main():
    htmls = grab_htmls([URL])

    for url, pages in htmls.items():
        tables = []

        for i, page in enumerate(pages):
            soup = BeautifulSoup(page, "lxml")

            title = soup.select_one("title").text.strip()
            print("TITLE:", title)

            zyzb_table = soup.select_one(".zyzb_table .report_table .table1")
            df = pd.read_html(StringIO(str(zyzb_table)))[0]

            if i != 0:
                df = df.iloc[:, 1:]

            tables.append(df)

        df = pd.concat(tables, axis=1, ignore_index=True)
        df.to_excel("build/zyzb_table.xlsx", index=False)

if __name__ == "__main__":
    main()

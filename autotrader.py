import traceback

from bs4 import BeautifulSoup
import pandas as pd
import requests
import json
# from itertools import cycle
import random
import time
import argparse


class App:
    output = {}
    productData = []

    def __init__(self, url, path):
        all_url = [url]
        for link in all_url:
            print(f'Start Url: {link}')
            pagListing = self.getPaginationUrl(link)
            print(f'pagListing Count:{len(pagListing)}')
            for pagUrl in pagListing:
                listingDict = self.getListing(pagUrl)
                print(f'listingCount per page:{len(listingDict["ProductUrl"])}')
                for Url in listingDict['ProductUrl']:
                    productDict = self.scrapedata(Url, pagUrl)
                    print(f'productData: {productDict}')
                    self.productData.append(productDict)
                    df = pd.DataFrame(self.productData)
                    df[['PaginationUrl', 'ProductUrl', 'Name', 'Trim', 'Year', 'Model', 'Make', 'Vin', 'StockNumber',
                        'PriceAnalysisDescription', 'Price', 'MainImageUrl', 'Dealer_Logo', 'Dealer_Name', 'Mileage',
                        'Description', 'Specifications', 'Features']].to_csv(f'{path} / Final_Output.csv')
                    self.output['Data'] = self.productData
                with open(f'{path}/Final_Output.json', "w") as outfile:
                    json.dump(self.output, outfile, indent=4)
        print("Complete Now Thanks You")

    def getPaginationUrl(self, link):
        paguinationUrl = []
        req = self.getRequest(link)
        makesoup = BeautifulSoup(req.text, "lxml")
        try:

            total_count = round(int(makesoup.find("span", {"id": "titleCount"}).text.strip().replace(',', '')) / 100)
            urlSplit = link.split('rcs=')
            for x in range(total_count):
                paguinationUrl.append(f'{urlSplit[0]}rcs={x * 100}{urlSplit[1].replace("0", "")}')
            return paguinationUrl
        except:
            traceback.print_exc()
            with open('autotrader.html','w') as f:
                f.write(req.text)

    def getRequest(self, link):
        time.sleep(10)
        user_agent_list = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36',
        ]
        user_agent = random.choice(user_agent_list)
        # Set the headers
        headers = {'User-Agent': user_agent}
        response = requests.get(link, headers=headers, timeout=10)
        return response

    def getListing(self, pagUrl):
        try:
            listing = {}
            listingSearchUrl = []
            listingName = []
            listingUrl = []
            req = self.getRequest(pagUrl)
            print(req.status_code)
            makesoup = BeautifulSoup(req.text, "lxml")

            for listUrl in makesoup.select('[class*="listing-details"] a'):
                listingSearchUrl.append(pagUrl)
                listingName.append(listUrl.text.strip())
                listingUrl.append(f'https://www.autotrader.ca{listUrl["href"]}')

            listing['SearchUrl'] = listingSearchUrl
            listing['Name'] = listingName
            listing['ProductUrl'] = listingUrl
            return listing
        except:
            print('Listing doesn\'t available')

    def scrapedata(self, productUrl, paginationUrl):
        productDetail = {}
        req = self.getRequest(productUrl)
        makesoup = BeautifulSoup(req.text, "lxml")
        print(req.status_code)

        try:
            for typ in makesoup.select('#wrapper > div.container-fluid > script[type="text/javascript"]'):
                data = typ.text.split('window[\'ngVdpModel\'] = ')[1].split('window[\'ngVdpGtm\'] = ')[0].replace(';',
                                                                                                                  '')
                dataOutput = json.loads(data)
                productDetail['PaginationUrl'] = paginationUrl
                productDetail['ProductUrl'] = productUrl
                productDetail['Name'] = dataOutput['deepLinkSavedSearch']['savedSearch']['title']
                productDetail['Trim'] = dataOutput['hero']['trim']
                productDetail['Year'] = dataOutput['hero']['year']
                productDetail['Model'] = dataOutput['hero']['model']
                productDetail['Make'] = dataOutput['hero']['make']
                productDetail['Vin'] = dataOutput['hero']['vin']
                productDetail['StockNumber'] = dataOutput['hero']['stockNumber']
                productDetail['PriceAnalysisDescription'] = dataOutput['hero']['priceAnalysisDescription']
                productDetail['Price'] = dataOutput['hero']['price']
                productDetail['MainImageUrl'] = dataOutput['gallery']['items'][0]['photoViewerUrl']
                productDetail['Dealer_Logo'] = dataOutput['dealerTrust']['logoUrl']
                productDetail['Dealer_Name'] = dataOutput['dealerTrust']['dealerCompanyName']
                productDetail['Mileage'] = dataOutput['hero']['mileage']
                productDetail['Description'] = dataOutput['description']['description'][0]['description']
                specification = pd.DataFrame(dataOutput['specifications']['specs'])
                specDict = specification[['key', 'value']]
                productDetail['Specifications'] = str(specDict)
                productDetail['Features'] = ', '.join(dataOutput['featureHighlights']['highlights'])
        except:
            pass
        return productDetail


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    url = 'https://www.autotrader.ca/cars/?rcp=100&rcs=0'
    parser.add_argument('--Url=', dest='Url', type=str, help='Add Url', default=url)
    parser.add_argument('--Path=', dest='Path', type=str, help='Add Path', default='autotrader')
    args = parser.parse_args()
    app = App(args.Url, args.Path)

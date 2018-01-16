# -*- coding: utf-8 -*-

import urlparse

import scrapy
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.exceptions import CloseSpider

from sc8.items import Sc8Item


class DrudgeSpider(CrawlSpider):
    name = 'drudge'
    def __init__(self, domains=None, *args, **kwargs):
        super(DrudgeSpider, self).__init__(*args, **kwargs)
        url = urlparse.urljoin(domains, '/')
        domain = url.split("//")[-1].split('/')[0]
        self.allowed_domains = [domain]
        self.start_urls = [url]
        
#     allowed_domains = ['indiaproperty.com']
#     start_urls = ['https://www.indiaproperty.com']

    rules = (
        Rule(LinkExtractor(allow=r''), callback='parse_item', follow=True),
    )
    count = 0

    #def start_requests(self):
        #payload = {"MapSearch": true, "LatLngBounds": -27.573605%2C153.038135%2C-27.605593%2C153.017665}
        #yield Request(url, self.parse_item, method="POST", body=urllib.urlencode(payload))

    def parse_item(self, response):
        self.count += 1
        i = Sc8Item()
        #i['domain_id'] = response.xpath('//input[@id="sid"]/@value').extract()
        #i['name'] = response.xpath('//div[@id="name"]').extract()
        #i['description'] = response.xpath('//div[@id="description"]').extract()
        i['details'] = response.url
        if self.count > 20:
            raise CloseSpider('bandwidth_exceeded')
        return i

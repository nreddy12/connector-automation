# -*- coding: utf-8 -*-

# Scrapy settings for sc8 project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'sc8'

SPIDER_MODULES = ['sc8.spiders']
NEWSPIDER_MODULE = 'sc8.spiders'
DOWNLOAD_DELAY = 1
USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:33.0) Gecko/20100101 Firefox/33.0"
# USER_AGENT = "scrapy"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'sc8 (+http://www.yourdomain.com)'

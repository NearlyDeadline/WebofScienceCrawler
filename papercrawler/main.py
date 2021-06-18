'''
Date: 2021-06-14 23:03:16
LastEditors: Mike
LastEditTime: 2021-06-17 18:45:47
FilePath: \PaperCrawler\papercrawler\main.py
'''
from scrapy import cmdline
import time

def crawl(queryFilePath = [], output_path = '../output', document_type = '', output_format = 'fieldtagged', sid: str = None):
    cmdline.execute(
        r'scrapy crawl wos_advanced_query_spider -a output_path={} -a output_format={}'.format(
            output_path, output_format).split() +
        ['-a', 'queryFilePath={}'.format(queryFilePath), '-a', 'document_type={}'.format(document_type), '-a', 'sid={}'.format(sid)])

if __name__ == '__main__':
    start_time = str(time.strftime('%Y-%m-%d-%H.%M.%S',time.localtime(time.time())))
    crawl(queryFilePath="E:\\PythonProjects\\PaperCrawler\\input\\error.txt")
    end_time = str(time.strftime('%Y-%m-%d-%H.%M.%S',time.localtime(time.time())))
    print(f"开始时间: {start_time}\n结束时间: {end_time}")
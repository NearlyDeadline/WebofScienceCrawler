'''
Date: 2021-06-14 23:03:16
LastEditors: Mike
LastEditTime: 2021-06-24 09:44:36
FilePath: \PaperCrawler\papercrawler\main.py
'''
from scrapy import cmdline


def crawl(query_file_path: str, output_dir, document_type="", output_format='fieldtagged'):
    cmdline.execute(
        r'scrapy crawl wos_advanced_query_spider -a output_dir={} -a output_format={}'.format(
            output_dir, output_format).split() +
        ['-a', 'query_file_path={}'.format(query_file_path), '-a', 'document_type={}'.format(document_type)])


if __name__ == '__main__':
    crawl(query_file_path="E:/PythonProjects/PaperCrawler/test/errortest.txt",
          output_dir='E:/PythonProjects/PaperCrawler/test/output'
          )

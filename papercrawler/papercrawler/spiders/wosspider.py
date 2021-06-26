'''
Date: 2021-06-13 22:58:40
LastEditors: Mike
LastEditTime: 2021-06-26 17:23:10
FilePath: \PaperCrawler\papercrawler\papercrawler\spiders\wosspider.py
'''
import scrapy
import re
from scrapy.http import Request
from scrapy.http import FormRequest
import time
from bs4 import BeautifulSoup
import os
import sys


class WosAdvancedQuerySpider(scrapy.Spider):
    name = 'wos_advanced_query_spider'
    allowed_domains = ['webofknowledge.com']
    start_urls = ['https://www.webofknowledge.com/']
    timestamp = str(time.strftime('%Y-%m-%d-%H.%M.%S', time.localtime(time.time())))
    end_year = time.strftime('%Y')

    # 提取URL中的SID和QID所需要的正则表达式
    sid_pattern = r'SID=(\w+)&'
    qid_pattern = r'qid=(\d+)&'

    # 提取已购买数据库的正则表达式
    db_pattern = r'WOS\.(\w+)'
    db_list = ['SCI', 'SSCI', 'AHCI', 'ISTP', 'ESCI', 'CCR', 'IC']

    output_path_prefix = ''

    sort_by = "RS.D;PY.D;AU.A;SO.A;VL.D;PG.A"  # 排序方式，相关性第一

    def __init__(self, query_file_path: str, output_dir: str, document_type: str = "",
                 output_format: str = 'fieldtagged', *args, **kwargs):
        '''
        @description: Web Of Science爬虫
        
        @param {query_file_path}: 保存所有查询式的文件的路径，要求文件内每一行为一篇论文的题目
               
               {output_dir}: 保存输出文件的文件夹，文件夹内每一个文件对应一篇论文的信息

               {document_type}: 检索文档的格式，默认留空代表检索网站上所有文档，其他取值为"Article"......

               {output_format}: 保存输出文件的格式，默认为'fieldtagged'纯文本
        '''
        super().__init__(*args, **kwargs)
        self.query_list = []
        self.output_path_prefix = output_dir
        self.document_type = document_type
        self.output_format = output_format
        self.sid = None
        self.qid_list = []

        if not query_file_path:
            print('请指定检索式文件路径')
            sys.exit(-1)

        with open(query_file_path) as query_file:
            self.query_list = list((map(lambda line: 'TI=(' + line.strip('\n').strip('.') + ')', query_file.readlines())))

        if output_dir is None:
            print('请指定有效的输出路径')
            sys.exit(-1)

        self.error_log_file_path = os.path.dirname(query_file_path) + '/wosspider_error_log.txt'
        self.write_error_log(self.timestamp)

    def parse(self, response):
        '''
        @description: 提交高级搜索请求
        '''

        pattern = re.compile(self.sid_pattern)
        result = re.search(pattern, response.url)
        if result is not None:
            self.sid = result.group(1)
            print('提取得到SID：', self.sid)
        else:
            print('SID提取失败')
            self.sid = None
            exit(-1)

        # 提交post高级搜索请求
        adv_search_url = 'https://apps.webofknowledge.com/WOS_AdvancedSearch.do'
        for q in self.query_list:
            query_form = {
                "product": "WOS",
                "search_mode": "AdvancedSearch",
                "SID": self.sid,
                "input_invalid_notice": "Search Error: Please enter a search term.",
                "input_invalid_notice_limits": " <br/>Note: Fields displayed in scrolling boxes must be combined with at least one other search field.",
                "action": "search",
                "replaceSetId": "",
                "goToPageLoc": "SearchHistoryTableBanner",
                "value(input1)": q,
                "value(searchOp)": "search",
                "value(select2)": "LA",
                "value(input2)": "",
                "value(select3)": "DT",
                "value(input3)": "",
                "value(limitCount)": "14",
                "limitStatus": "expanded",
                "ss_lemmatization": "On",
                "ss_spellchecking": "Suggest",
                "SinceLastVisit_UTC": "",
                "SinceLastVisit_DATE": "",
                "period": "Range Selection",
                "range": "ALL",
                "startYear": "1900",
                "endYear": self.end_year,
                "editions": self.db_list,
                "update_back2search_link_param": "yes",
                "ss_query_language": "",
                "rs_sort_by": self.sort_by,
            }

            yield FormRequest(adv_search_url, method='POST', formdata=query_form, dont_filter=True,
                              callback=self.parse_query_response,
                              meta={'sid': self.sid, 'query': q})

    def parse_query_response(self, response):
        '''
        @description: 找到高级检索结果入口链接，同时还要记录下QID
        '''
        sid = response.meta['sid']
        query = response.meta['query']

        # 通过bs4解析html找到检索结果的入口
        soup = BeautifulSoup(response.text, 'lxml')
        entry = soup.find('a', attrs={'title': 'Click to view the results'})
        if entry:
            entry_url = 'https://apps.webofknowledge.com' + entry.get('href')

            # 找到入口url中的QID，存放起来以供下一步处理函数使用
            pattern = re.compile(self.qid_pattern)
            result = re.search(pattern, entry_url)
            if result is not None:
                qid = result.group(1)
                print('提取得到qid：', qid)
                if qid in self.qid_list:
                    self.write_error_log(f"Duplicate qid. Probably because the query '{query}' got nothing.")
                    return
                self.qid_list.append(qid)
            else:
                qid = None
                print('qid提取失败')
                exit(-1)

            yield Request(entry_url, callback=self.parse_download_link,
                          meta={'sid': sid, 'query': query, 'qid': qid})
        else:
            pass

    def parse_download_link(self, response):
        '''
        @description: 从搜索结果中选择需要下载哪些文献
        '''
        sid = response.meta['sid']
        query = response.meta['query']
        qid = response.meta['qid']

        # 爬第一篇
        start = 1
        end = 1
        paper_num = 1

        output_form = {
            "selectedIds": "",
            "displayCitedRefs": "true",
            "displayTimesCited": "true",
            "displayUsageInfo": "true",
            "viewType": "summary",
            "product": "WOS",
            "rurl": response.url,
            "mark_id": "WOS",
            "colName": "WOS",
            "search_mode": "AdvancedSearch",
            "locale": "en_US",
            "view_name": "WOS-summary",
            "sortBy": self.sort_by,
            "mode": "OpenOutputService",
            "qid": str(qid),
            "SID": str(sid),
            "format": "saveToFile",
            "filters": "HIGHLY_CITED HOT_PAPER OPEN_ACCESS PMID USAGEIND AUTHORSIDENTIFIERS ACCESSION_NUM FUNDING SUBJECT_CATEGORY JCR_CATEGORY LANG IDS PAGEC SABBR CITREFC ISSN PUBINFO KEYWORDS CITTIMES ADDRS CONFERENCE_SPONSORS DOCTYPE CITREF ABSTRACT CONFERENCE_INFO SOURCE TITLE AUTHORS  ",
            "mark_to": str(end),
            "mark_from": str(start),
            "queryNatural": str(query),
            "count_new_items_marked": "0",
            "use_two_ets": "false",
            "IncitesEntitled": "yes",
            "value(record_select_type)": "range",
            "markFrom": str(start),
            "markTo": str(end),
            "fields_selection": "HIGHLY_CITED HOT_PAPER OPEN_ACCESS PMID USAGEIND AUTHORSIDENTIFIERS ACCESSION_NUM FUNDING SUBJECT_CATEGORY JCR_CATEGORY LANG IDS PAGEC SABBR CITREFC ISSN PUBINFO KEYWORDS CITTIMES ADDRS CONFERENCE_SPONSORS DOCTYPE CITREF ABSTRACT CONFERENCE_INFO SOURCE TITLE AUTHORS  ",
            "save_options": self.output_format
        }

        output_url = 'https://apps.webofknowledge.com/OutboundService.do?action=go&&'
        yield FormRequest(output_url, method='POST', formdata=output_form, dont_filter=True,
                          callback=self.download,
                          meta={'sid': sid, 'query': query, 'qid': qid})

    def download(self, response):
        '''
        @description: 下载文献，并将下载的文献与query做对比，如果下载错了，就改为写入错误日志
        '''
        file_postfix_pattern = re.compile(r'filename=\w+\.(\w+)$')
        file_postfix = re.search(file_postfix_pattern, response.headers[b'Content-Disposition'].decode())
        if file_postfix is not None:
            file_postfix = file_postfix.group(1)
        else:
            print('找不到文件原始后缀，使用txt后缀保存')
            file_postfix = 'txt'

        sid = response.meta['sid']
        query = response.meta['query']
        qid = response.meta['qid']

        text = response.text

        filter_cond = lambda c: str.isalpha(c)
        expect_title = ''.join(filter(filter_cond, self.get_title_from_query(query).lower()))
        got_title = ''.join(filter(filter_cond, self.get_title_from_response(text).lower()))

        # 保存为文件
        if expect_title == got_title:
            filename = self.output_path_prefix + '/advanced_query/{}.{}'.format(qid, file_postfix)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(text)
        else:
            self.write_error_log(f"Title not compatible: Expect '{expect_title}', but got '{got_title}'.")

    def get_title_from_response(self, response: str) -> str:
        '''
        @description: 从网页response获取文献题目
        
        @param {response}
        
        @return {str}: 文献题目
        '''
        ti_pattern = '\nTI '
        ti_index = response.find(ti_pattern)
        text_title = ''
        i = ti_index + len(ti_pattern)
        while response[i] != '\n':
            text_title = text_title + response[i]
            i = i + 1
        return text_title

    def get_title_from_query(self, query: str) -> str:
        '''
        @description: 从query查询式获取文献题目，将'TI=('前四个字符，与最后一个')'字符去掉即可
        '''
        return query[4:-1]

    def write_error_log(self, text: str):
        '''
        @description: 写入错误日志文件的函数
        '''
        with open(self.error_log_file_path, 'a') as error_log:
            error_log.write(text + '\n')

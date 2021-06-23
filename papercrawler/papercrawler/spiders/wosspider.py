'''
Date: 2021-06-13 22:58:40
LastEditors: Mike
LastEditTime: 2021-06-23 17:23:03
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
    
class WosAdvancedQuerySpiderSpider(scrapy.Spider):
    name = 'wos_advanced_query_spider'
    allowed_domains = ['webofknowledge.com']
    start_urls = ['http://www.webofknowledge.com/']
    timestamp = str(time.strftime('%Y-%m-%d-%H.%M.%S',time.localtime(time.time())))
    end_year = time.strftime('%Y')

    #提取URL中的SID和QID所需要的正则表达式
    sid_pattern = r'SID=(\w+)&'
    qid_pattern = r'qid=(\d+)&'

    # 提取已购买数据库的正则表达式
    db_pattern = r'WOS\.(\w+)'
    db_list = ['SCI', 'SSCI', 'AHCI', 'ISTP', 'ESCI', 'CCR', 'IC']

    output_path_prefix = ''
    error_log_file_path = './wosspider_error_log.txt'

    sort_by = "RS.D;PY.D;AU.A;SO.A;VL.D;PG.A" # 排序方式，相关性第一

    def __init__(self, query_file_path: str, output_dir: str, document_type: str, output_format: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = [] # 检索式集合
        self.output_path_prefix = output_dir
        self.document_type = document_type # 目标文献类型
        self.output_format = output_format # 导出文献格式
        self.sid = None

        if not query_file_path:
            print('请指定检索式文件路径')
            sys.exit(-1)
            
        with open(query_file_path) as query_file:
            for line in query_file.readlines():
                line = line.strip('\n')
                line = line[0:-1] # 把最后的.去掉
                if line is not None:
                    self.query.append('TI=(' + line + ')') # 加个括号，防止题目内的and等词语被视为布尔操作符
        
        if output_dir is None:
            print('请指定有效的输出路径')
            sys.exit(-1)

    def parse(self, response):
        """
        提交高级搜索请求，将高级搜索请求返回给parse_result_entry处理

        :param response:
        :return:
        """

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
        adv_search_url = 'http://apps.webofknowledge.com/WOS_AdvancedSearch.do'
        for q in self.query:
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

            #将这一个高级搜索请求yield给parse_result_entry，内容为检索历史记录，包含检索结果的入口
            #同时通过meta参数为下一个处理函数传递sid、journal_name等有用信息
            yield FormRequest(adv_search_url, method='POST', formdata=query_form, dont_filter=True,
                            callback=self.parse_result_entry,
                            meta={'sid': self.sid, 'query': q})

    def parse_result_entry(self, response):
        """
        找到高级检索结果入口链接，交给parse_results处理
        同时还要记录下QID
        :param response:
        :return:
        """
        sid = response.meta['sid']
        query = response.meta['query']

        #通过bs4解析html找到检索结果的入口
        soup = BeautifulSoup(response.text, 'lxml')
        entry = soup.find('a', attrs={'title': 'Click to view the results'})
        if entry:
            entry_url = 'http://apps.webofknowledge.com' + entry.get('href')

            #找到入口url中的QID，存放起来以供下一步处理函数使用
            pattern = re.compile(self.qid_pattern)
            result = re.search(pattern, entry_url)
            if result is not None:
                qid = result.group(1)
                print('提取得到qid：', qid)
            else:
                qid = None
                print('qid提取失败')
                exit(-1)

            #yield一个Request给parse_result，让它去处理搜索结果页面，同时用meta传递有用参数
            yield Request(entry_url, callback=self.parse_results,
                        meta={'sid': sid, 'query': query, 'qid': qid})
        else:
            pass
        
    def parse_results(self, response):
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
            "IncitesEntitled": "no",
            "value(record_select_type)": "range",
            "markFrom": str(start),
            "markTo": str(end),
            "fields_selection": "HIGHLY_CITED HOT_PAPER OPEN_ACCESS PMID USAGEIND AUTHORSIDENTIFIERS ACCESSION_NUM FUNDING SUBJECT_CATEGORY JCR_CATEGORY LANG IDS PAGEC SABBR CITREFC ISSN PUBINFO KEYWORDS CITTIMES ADDRS CONFERENCE_SPONSORS DOCTYPE CITREF ABSTRACT CONFERENCE_INFO SOURCE TITLE AUTHORS  ",
            "save_options": self.output_format
        }

        #将下载地址yield一个FormRequest给download_result函数，传递有用参数
        output_url = 'http://apps.webofknowledge.com/OutboundService.do?action=go&&'
        yield FormRequest(output_url, method='POST', formdata=output_form, dont_filter=True,
                            callback=self.download_result,
                            meta={'sid': sid, 'query': query, 'qid': qid})

    def download_result(self, response):

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
        got_title    = ''.join(filter(filter_cond, self.get_title_from_response(text).lower()))

        # 保存为文件
        if expect_title == got_title:
            filename = self.output_path_prefix + '/advanced_query/{}.{}'.format(qid, file_postfix)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(text)
        else:
            with open(self.error_log_file_path, 'a') as error_log:
                error_log.write(f"Title not compatible: Expect '{expect_title}', but got '{got_title}'.\n")
    
    def get_title_from_response(self, response: str) -> str:
        ti_pattern = '\nTI '
        ti_index = response.find(ti_pattern)
        text_title = ''
        i = ti_index + len(ti_pattern)
        while response[i] != '\n':
            text_title = text_title + response[i]
            i = i + 1
        return text_title

    def get_title_from_query(self, query: str) -> str:
        return query[4:-1]

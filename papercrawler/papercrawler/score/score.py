'''
Date: 2021-06-27 16:29:43
LastEditors: Mike
LastEditTime: 2021-06-27 16:59:43
FilePath: \PaperCrawler\papercrawler\papercrawler\score\score.py
'''

import json

def score(paper_path: str, journal_list_path: str):
    '''
    @description: 输入爬取到的论文信息，到期刊列表中查找该论文发表期刊的影响因子等评分值
    
    @param {paper_path: str} 论文文件路径
           {journal_list_path: str} 期刊列表json文件路径
    
    @return {dict} json object
    '''    
    with open(paper_path) as p:
        pattern = "SO "
        journal_name = ''.join(list(filter(lambda line: line.startswith(pattern), p.readlines()))[0][len(pattern):]).strip()
        
    with open(journal_list_path) as j:
        journal_list = json.load(j)
    return journal_list.get(journal_name)


if __name__ == '__main__':
    paper_path = 'E:/PythonProjects/PaperCrawler/test/output/advanced_query/7.txt'
    journal_list_path = 'E:/PythonProjects/PaperCrawler/papercrawler/papercrawler/journal_list/journal_list.json'
    print(score(paper_path, journal_list_path))
'''
Date: 2021-06-26 17:50:46
LastEditors: Mike
LastEditTime: 2021-06-26 23:24:24
FilePath: \PaperCrawler\papercrawler\papercrawler\journal_list\journal_list.py
'''
import csv
import json
import os

'''
    key: str -> Full Journal Title
    value: dict
        key: str -> Journal Impact Factor
        value: float

        key: str -> Eigenfactor Score
        value: float

        key -> Field Rank
        value: list[dict]
            key: str -> Field Name
            value: int -> Rank
'''

def get_json(journal_folder_path: str) -> dict:
    '''
    @description: 获取json格式的期刊信息，默认保存于当前文件夹
    
    @param {journal_folder_path: str} 保存原始文件——csv格式的期刊信息的文件夹的路径。其内的文件须以该期刊所在的领域为文件名
    
    @return {journal_dict: dict} 获得dict格式的期刊信息，可直接使用json等方法保存
    '''    
    journal_dict = {}
    journal_fields = list(map(lambda t: os.path.splitext(t)[0], os.listdir(journal_folder_path)))
    for journal_field in journal_fields:
        with open(journal_folder_path + '/' + journal_field + '.csv') as journal_file:
            field_csv = csv.reader(journal_file)
            for row in filter(lambda row: str.isdigit(row[0]), field_csv):
                journal_dict_key = row[1]

                journal_dict_value = {}
                journal_dict_value['Journal Impact Factor'] = row[3]
                journal_dict_value['Eigenfactor Score'] = row[4]

                journal_dict_value['Field Rank'] = []
                previous_journal_dict_value = journal_dict.get(journal_dict_key)
                if previous_journal_dict_value:
                    journal_dict_value['Field Rank'] = previous_journal_dict_value['Field Rank']

                field_rank_dict = {}
                field_rank_dict['Field Name'] = journal_field
                field_rank_dict['Rank'] = row[0]
                journal_dict_value['Field Rank'].append(field_rank_dict)

                journal_dict[journal_dict_key] = journal_dict_value
    return journal_dict

class Journal():
    def __init__(self, impact_factor: float, eigenfactor: float):
        self.impact_factor = impact_factor
        self.eigenfactor = eigenfactor
        self.field_rank_list = []
        
    def add_field_rank(self, field_name: str, rank: int):
        field_rank = FieldRank(field_name, rank)
        self.field_rank_list.append(field_rank)

class FieldRank():
    def __init__(self, field_name: str, rank: int):
        self.field_name = field_name
        self.rank = rank

def get_variable(journal_folder_path: str) -> dict:
    '''
    @description: 获取对象化的期刊信息，具体类定义见Journal与FieldRank类
    
    @param {journal_folder_path: str} 保存原始文件——csv格式的期刊信息的文件夹的路径。其内的文件须以该期刊所在的领域为文件名
    
    @return {journal_dict: dict} 获得dict格式的期刊信息，键为期刊名，值为Journal对象
    '''    
    journal_dict = {}
    journal_fields = list(map(lambda t: os.path.splitext(t)[0], os.listdir(journal_folder_path)))
    for journal_field in journal_fields:
        with open(journal_folder_path + '/' + journal_field + '.csv') as journal_file:
            field_csv = csv.reader(journal_file)
            for row in filter(lambda row: str.isdigit(row[0]), field_csv):
                full_title = row[1]
                
                previous_value = journal_dict.get(full_title)
                if not previous_value:
                    impact_factor = row[3]
                    eigenfactor = row[4]
                    journal_dict[full_title] = Journal(impact_factor, eigenfactor)

                journal_dict[full_title].add_field_rank(journal_field, row[0])
    return journal_dict

if __name__ == '__main__':
    journal_folder_path = 'E:/PythonProjects/PaperCrawler/test/journal'
    
    journal_dict = get_json(journal_folder_path)
    s = json.dumps(journal_dict, indent=4)
    with open('./journal_list.json', 'w') as journal_json:
        journal_json.write(s)

    v = get_variable(journal_folder_path)
    print("end")
    
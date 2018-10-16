# -*- coding: utf-8 -*-

import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import pypinyin


class ElasticSearch(object):
    def __init__(self, index_name="military_db", index_type="military_ner", ip="127.0.0.1", port=9200):
        """
        :param index_name:索引名称
        :param index_type:索引类型
        :param ip:ip
        :param port:port
        """
        self.index_name = index_name
        self.index_type = index_type
        # 无用户名密码状态
        self.es = Elasticsearch([ip], port=port)
        # 用户名密码状态
        # self.es = Elasticsearch([ip], http_auth=('elastic', 'password'), port=port)


    def create_index(self):
        """
        创建索引
        :return:
        """
        _index_mappings = {
            "mappings": {
                self.index_type: {
                    "properties": {
                        "hanzi_cut": {  # 存储待搜索项，分词
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_max_word"
                        },
                        "hanzi": {  # 存储待搜索项，不分词
                            "type": "keyword"
                        },
                        "pinyin_cut": {
                            "type": "text"
                        },
                        "pinyin": {
                            "type": "keyword"
                        },
                        "abbreviate": {
                            "type": "keyword"
                        },
                        "weight": {      # 存储权重
                            "type": "float"
                        }
                    }
                }
            }
        }

        if not self.es.indices.exists(index=self.index_name):
            res = self.es.indices.create(index=self.index_name, body=_index_mappings)
            if res['acknowledged']:
                print('index "{}" create success !!!'.format(self.index_name))
            else:
                print('index "{}" create error, message: {} !!!'.format(self.index_name, res))
        else:
            print("index_name: '{}' is exist!!!".format(self.index_name))
            sys.exit(0)

    def delete_index(self, index_name=None):
        """
        删除索引
        :param index_name:索引名称
        :return:
        """
        if not index_name:
            index_name = self.index_name
        res = self.es.indices.delete(index=index_name, ignore=[400, 404])
        print(res)
        try:
            if res['acknowledged']:
                print("delete index '{}' success!!!".format(index_name))
        except Exception as e:
            print("delete index '{}' error, message: {}".format(index_name, res))

    def get_pinyin_and_abbreviate(self, string):
        pinyin = pypinyin.lazy_pinyin(string)
        abbreviate = ''.join([item[0] for item in pinyin])
        pinyin_cut = ' '.join(pinyin)
        return ''.join(pinyin), pinyin_cut, abbreviate

    def add_data_by_list(self, list_str):
        """
        通过列表向 self.index_name 中添加数据
        :param list_str: ['飞机', '导弹']
        :return:
        """
        actions = []
        for data, weight in list_str:
            pinyin, pinyin_cut, abbreviate = self.get_pinyin_and_abbreviate(data)
            temp = {"_index": self.index_name,
                    "_type": self.index_type,
                    "_source": {"hanzi": data, "hanzi_cut": data,
                                "weight": weight, "abbreviate": abbreviate,
                                "pinyin_cut": pinyin_cut, "pinyin": pinyin}
                    }
            actions.append(temp)
        success, _ = bulk(self.es, actions, index=self.index_name, raise_on_error=True)
        print('Performed %d actions' % success)

    def add_data_by_file(self, file_path):
        """
        通过文件向 self.index_name 中添加数据
        :param file_path: 每行存储一条数据
        :return:
        """
        list_str = []
        with open(file_path, 'r') as f:
            for line in f:
                if not line.startswith('#'):
                    lis = line.strip().split('\t')
                    # print(lis)
                    if len(lis) > 1:
                        list_str.append((lis[0], float(lis[1])))
                    else:
                        list_str.append((lis[0], 1.0))
        self.add_data_by_list(list_str)

    def is_chinese(self, string):
        """
        判断一个字符串是否包含汉字
        :param string:
        :return:
            0：全部中文
            1：全部英文
            2：中英混合
        """
        eng = 0
        chi = 0
        for word in string:
            if u'\u4e00' <= word <= u'\u9fa5':
                chi += 1
            else:
                eng += 1
        if eng == 0:
            return 0
        if chi == 0:
            return 1
        return 2

    def search_data_pattern(self, query_word, mode='0', field='hanzi_cut', return_size=10):
        """
        搜索模式
        :param query_word:
        :param mode: 匹配模式, 默认为0
        :param return_size:
        :return:
        """
        search_result = {}
        keyword = ''

        if mode == '0':
            mode = 'match'
            field = 'hanzi_cut'
            keyword = query_word

        if mode == '1':
            mode = 'fuzzy'
            field = 'hanzi'
            keyword = query_word

        if mode == '2':
            mode = 'regexp'
            field = 'pinyin'
            keyword = '.*'+query_word+'.*'

        if mode == '3':
            mode = 'regexp'
            field = 'abbreviate'
            keyword = '.*'+query_word+'.*'

        doc = {
            "query": {
                mode: {
                    field: keyword
                }
            },
            "size": return_size
        }

        _searched = self.es.search(index=self.index_name, doc_type=self.index_type, body=doc)
        for hit in _searched['hits']['hits']:
            # print(hit)
            search_result[hit['_source']['hanzi']] = hit['_source']['weight']
        return search_result

    def _search_data_all_chinese(self, query_word, return_size=10):
        """
        所搜全部中文
        :param query_word:
        :param return_size:
        :return:
        """
        ret_result = {}
        search_data_by_mode0 = self.search_data_pattern(query_word, mode='0', return_size=return_size)
        search_data_by_mode1 = self.search_data_pattern(query_word, mode='1', return_size=return_size)
        # print(search_data_by_mode0, search_data_by_mode1)
        ret_result.update(search_data_by_mode0)
        ret_result.update(search_data_by_mode1)
        return ret_result

    def _search_data_all_english(self, query_word, return_size):
        """
        搜索全部英文
        :param query_word:
        :param return_size:
        :return:
        """
        ret_result = {}
        search_data_by_mode2 = self.search_data_pattern(query_word, mode='2', return_size=return_size)
        search_data_by_mode3 = self.search_data_pattern(query_word, mode='3', return_size=return_size)
        ret_result.update(search_data_by_mode2)
        ret_result.update(search_data_by_mode3)
        return ret_result

    def _search_mix_chinese_english(self, query_word, return_size=10):
        """
        搜索中英混合词
        :param query_word:
        :param return_size:
        :return:
        """
        ret_result = {}
        query_word_english = self._trans_query_to_pinyin(query_word)
        # 1. 直接根据中文进行搜索
        ret_result1 = self._search_data_all_chinese(query_word, return_size=return_size)
        # 2. 将中文部分转换成拼音，进行搜索
        ret_result2 = self._search_data_all_english(query_word_english, return_size=return_size)
        ret_result.update(ret_result1)
        ret_result.update(ret_result2)
        return ret_result

    def _trans_query_to_pinyin(self, query_word):
        """
        转换中文到英文
        :param query_word:
        :return:
        """
        pinyins = pypinyin.lazy_pinyin(query_word)
        return "".join(pinyins)

    def search_data(self, query_word, return_size=10):
        """
        根据关键词进行搜索
        :param query_word: 查询词
        :param return_size: 返回词个数
        :return:
        """
        ret_result = {}
        query_pattern = self.is_chinese(query_word)
        # 如果输入中包含中文，则采用分词模式和模糊搜索模式进行数据搜索
        if query_pattern == 0:
            ret_result = self._search_data_all_chinese(query_word, return_size=return_size)
        # 如果输入中不包含中文，则采用拼音及缩写词进行模糊搜索
        elif query_word == 1:
            ret_result = self._search_data_all_english(query_word, return_size=return_size)
        # 中英文混合输入
        # 1.直接采用中文分词进行匹配 2.将中文转化成拼音，然后采用英文进行匹配
        else:
            ret_result = self._search_mix_chinese_english(query_word, return_size=return_size)

        # for key, val in ret_result.items():
        #     if val != 1:
        #         ret_result = sorted(ret_result.items(), key=lambda item: item[1], reverse=True)
        #         break
        return self.format_result(query_word, ret_result)

    def suggestion(self, query_word, return_size=10):
        query_word_pinyin = self._trans_query_to_pinyin(query_word)
        suggestion_result = {}

        mode = 'regexp'
        fields = ['hanzi', 'pinyin', 'abbreviate']

        for query_word in [query_word, query_word_pinyin]:
            keyword = query_word + '.*'
            for field in fields:
                temp_result = {}
                doc = {
                    "query": {
                        mode: {
                            field: keyword
                        }
                    },
                    "size": return_size
                }
                _searched = self.es.search(index=self.index_name, doc_type=self.index_type, body=doc)
                for hit in _searched['hits']['hits']:
                    temp_result[hit['_source']['hanzi']] = hit['_source']['weight']
                suggestion_result.update(temp_result)
        ret_result = self.format_result(query_word, suggestion_result)
        return ret_result

    def format_result(self, query_word, ret_result):
        """
        将搜索结果按照权重分成大于1和等于1 两部分；
        大于1部分按照权重进行排序， 等于1部分按照编辑距离进行排序；
        大于1部分优先级大于 等于1部分。
        :param ret_result:
        :return:
        """
        weight_large_1 = {}
        weight_equal_1 = {}
        for key, val in ret_result.items():
            if val > 1:
                weight_large_1[key] = val
            else:
                weight_equal_1[key] = val

        edit_result = {}
        for key, val in weight_equal_1.items():
            edit_result[key] = self.edit(query_word, key)

        weight_equal_1_sort = sorted(edit_result.items(), key=lambda item: item[1], reverse=False)
        weight_equal_1_sort = [(key, 1.0) for key, val in weight_equal_1_sort]

        weight_large_1_sort = sorted(weight_large_1.items(), key=lambda item: item[1], reverse=True)
        weight_large_1_sort.extend(weight_equal_1_sort)
        return weight_large_1_sort

    def edit(self, str1, str2):
        """计算两个文本字符串中的最小编辑距离"""
        matrix = [[i + j for j in range(len(str2) + 1)] for i in range(len(str1) + 1)]
        for i in range(1, len(str1) + 1):
            for j in range(1, len(str2) + 1):
                if str1[i - 1] == str2[j - 1]:
                    d = 0
                else:
                    d = 1
                matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + d)

        return matrix[len(str1)][len(str2)]

    def delete_data_by_id(self, id):
        """
        根据id删除一条记录
        :param id:
        :return:
        """
        res = self.es.delete(index=self.index_name, doc_type=self.index_type, id=id)
        print('delete {} data !!!'.format(res['deleted']))

    def delete_data_by_keyword(self, keyword, mode="match_phrase"):
        """
        根据关键词删除数据，会删除包含该关键词的多条数据
        :param keyword:
        :param mode: 搜索关键词的模式，
                     match:模糊匹配，首先对keyword进行分词，然后搜索；
                     match_phrase:先分词，再根据分词序列全匹配；
                     regexp:正则匹配
        :return:
        """
        field = 'content'
        if mode == 'regexp':
            field = 'content_all'

        query = {
            "query": {
                mode: {
                    field: keyword
                }
            }
        }
        res = self.es.delete_by_query(index=self.index_name, doc_type=self.index_type, body=query)
        print('delete {} data !!!'.format(res['deleted']))

    def delete_all_doc(self):
        """
        删除所有文档
        :return:
        """
        query = {
            "query": {
                "match_all": {
                }
            }
        }
        res = self.es.delete_by_query(index=self.index_name, doc_type=self.index_type, body=query)
        print('delete {} data !!!'.format(res['deleted']))


def test(elastic_search):
    print("搜索：")
    for query in ['东风导弹', '坦克 99', '华shengdun', '克来姆森级驱逐舰', 'dongfeng', 'df', 'hwj', 'zjg']:
        ret = elastic_search.search_data(query, return_size=10)
        print("{} ==> {}".format(query, ret))

    print("\n\n提示：")
    for query in ['东风', 'dongfeng', 'hsd', '华shengdun']:
        ret = elastic_search.suggestion(query, return_size=10)
        print("{} ==> {}".format(query, ret))


if __name__ == '__main__':
    elastic_search = ElasticSearch()
    # elastic_search.delete_index()
    # elastic_search.create_index()
    # elastic_search.add_data_by_file('./arms.txt')
    test(elastic_search)
    # print(elastic_search.get_pinyin_and_abbreviate('弹道导弹'))





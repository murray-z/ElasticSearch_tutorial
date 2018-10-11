# Elasticsearch简明教程

# Elasticsearch

## 1.安装
- 安装Elasticsearch

```shell
$ wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-6.4.1.zip 
$ unzip elasticsearch-6.4.1.zip
$ cd elasticsearch-6.4.1/ 
```

- 安装中文分词工具
```shell
$ ./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v6.4.1/elasticsearch-analysis-ik-6.4.1.zip
```

## 2.启动
```shell
$ ./bin/elasticsearch
```


# python使用示例

## 1. 安装
```shell
pip install elasticsearch
```

## 2. 实例化
```python
from elasticsearch import Elasticsearch
es = Elasticsearch(["ip"], port=9200) 
```

## 3. 新建索引
```python
_index_mappings = {
            "mappings": {
                "index_type": {      # index_type: 索引类型，自己命名
                    "properties": {
                        "content": {  # content: 字段名称，自己命名
                            "type": "text",
                            "analyzer": "ik_max_word",   # analyzer, search_analyzer: 分词模式（ik_max_word|ik_smart）
                            "search_analyzer": "ik_max_word"
                        },
                        "content_all": {  # content_all: 字段名称
                            "type": "keyword"  # 此时不分词
                        }
                    }
                }

            }
        }

# index: 索引名称
res = es.indices.create(index="index_name", body=_index_mappings)
```
## 4. 插入数据
### 4.1 插入单条数据
```python
data = {
    "content": "东风21中程弹道导弹",
    "content_all": "东风21中程弹道导弹"
}

res = es.index(index="index_name", doc_type="index_type", body=data)
```

### 4.2 批量插入数据
```python
list_str = ['东风21中程弹道导弹', '东风31洲际弹道导弹', '东风41洲际弹道导弹', '巨浪潜射弹道导弹']
actions = []
for data in list_str:
    temp = {"_index": 'index_name',
            "_type": 'index_type',
            "_source": {"content": data, "content_all": data}
            }
    actions.append(temp)
success, _ = bulk(es, actions, index='index_name', raise_on_error=True)
```

## 5. 搜索数据
### 5.1 match
- 先对keyword分词，只要匹配一个关键词就输出
- 输入
```python
doc = {
    "query": {
        "match": {
            "content": "东风导弹"    # 搜索字段名称: 关键词
        }
    },
    "size": 10   # 返回结果个数
}
```
- 搜索
```python
search_result = []
_searched = es.search(index='index_name', doc_type='index_type', body=doc)
for hit in _searched['hits']['hits']:
    search_result.append(hit['_source']['content'])
print(search_result)
```
- 结果
<pre>
['东风21中程弹道导弹', '东风31洲际弹道导弹', '东风41洲际弹道导弹', '新型隐身导弹艇']
</pre>


### 5.2 match_phrase
- 先分词，再按分词序列进行搜索，此时考虑词序，且待搜索项必须包含所有词
- 输入
```python
doc = {
    "query": {
        "match_phrase": {
            "content": "弹道导弹"
        }
    },
    "size": 10
}
```
- 搜索
```python
search_result = []
_searched = es.search(index='index_name', doc_type='index_type', body=doc)
for hit in _searched['hits']['hits']:
    search_result.append(hit['_source']['content'])
print(search_result)
```
- 结果
<pre>
['巨浪潜射弹道导弹', '东风31洲际弹道导弹', '东风21中程弹道导弹', '东风41洲际弹道导弹']
</pre>

### 5.3 regexp
- 此时keyword为正则表达式，按照正则表达式进行搜索；可以用此功能实现语义联想（"keyword.*"）
- 输入
```python
doc = {
    "query": {
        "regexp": {
            "content_all": "东风.*" 
        }
    },
    "size": return_size
}
```

- 搜索
```python
search_result = []
_searched = es.search(index='index_name', doc_type='index_type', body=doc)
for hit in _searched['hits']['hits']:
    search_result.append(hit['_source']['content'])
print(search_result)
```
- 结果
<pre>
['东风21中程弹道导弹', '东风31洲际弹道导弹', '东风41洲际弹道导弹']
</pre>


### 5.4 fuzzy
- 模糊搜索模式，此时可以实现对关键词进行纠错
- 输入
```python
doc = {
    "query": {
        "fuzzy": {
            "content_all": "桑拿普森级驱逐舰"
        }
    },
    "size": 10
}
```

- 搜索
```python
search_result = []
_searched = es.search(index='index_name', doc_type='index_type', body=doc)
for hit in _searched['hits']['hits']:
    search_result.append(hit['_source']['content'])
print(search_result)
```
- 结果
<pre>
['桑普森级驱逐舰']
</pre>

## 6. 删除数据
### 6.1 根据id进行删除
```python
es.delete(index='index_name', doc_type='index_type', id=1)
```

### 6.2 根据query删除
```python
query = {
    "query": {
        "match": {
            "content": "导弹"
        }
    }
}
res = es.delete_by_query(index='index_name', doc_type='index_type', body=query)
```


# 参考
- [Elasticsearch官网](https://www.elastic.co/products/elasticsearch)
- [ik-中文分词工具](https://github.com/medcl/elasticsearch-analysis-ik/)
- [Elasticsearch 入门教程](http://www.ruanyifeng.com/blog/2017/08/elasticsearch.html)
- [Elasticsearch 权威指南（中文版）](https://es.xiaoleilu.com/index.html)

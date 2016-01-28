#coding=utf-8 

import re
import jieba
import logging
from gensim import corpora, models, similarities
from main import*

def processPair():
    conversation = {}
    f = open('original.pair')
    p = re.compile(r'(\d+)(\D?)(.*)', re.S)
    for line in f.readlines():
        m = p.match(line)
        if m:
            vl = m.groups()[2][:-1].split(',')
            key = int(m.groups()[0])    
            value = []
            for sv in vl:
                value.append(int(sv))
            conversation[key] = value
    return conversation
    # print(conversation[177])

def processPosts():
    posts = {}
    f = open('post.index', encoding= 'utf8')
    p = re.compile(r'(\d+)(\D{2})(.*)', re.S)
    for line in f.readlines():
        m = p.match(line)
        if m:
            vl = m.groups()[2][:-1].split()
            key = int(m.groups()[0])
            value = ''.join(vl)
            posts[key] = value
    return posts
    # print(posts[122])

def processResponses():
    responses = {}
    f = open('response.index', encoding= 'utf8')
    p = re.compile(r'(\d+)(\D{2})(.*)', re.S)
    for line in f.readlines():
        m = p.match(line)
        if m:
            vl = m.groups()[2][:-1].split()
            key = int(m.groups()[0])
            value = ''.join(vl)
            if value[0] == u':':
                value = value[1:]
            if value[0:3] == u'回复:':
                value = value[3:]
            if value[0:6] == u'转发此微博:':
                value = value[6:]
            responses[key] = value
    return responses
    # print(responses[38141])

def dumpDatabase(n):
    storage = JsonDatabase('database.db')
    conversation = processPair()
    print('done pairs')
    posts = processPosts()
    print('done posts')
    responses = processResponses()
    print('done responses')
    for i in range(n): #38016
        if i in conversation:
            relist = conversation[i]
            response_texts = []
            for j in relist:
                response_texts.append(responses[j])

        database_values = storage.find(posts[i])
        if not database_values:
            storage.insert(posts[i], {})
        storage.update(posts[i], response=response_texts)

def deleteStopwords(sentence):
    stopwords = {}.fromkeys([u'的',u'了'])
    segs = jieba.cut(sentence)
    goal = ''
    for s in segs:
        if s not in stopwords:
            goal += s
    return goal

if __name__ == '__main__':
    dumpDatabase(10)

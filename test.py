#coding=utf-8 

from __future__ import division
import random
from jsondb.db import Database
import jieba
from create import*

class JsonDatabase(object):

    def __init__(self, database_path):
        self.database = Database(database_path)

    def find(self, key):
        return self.database.data(key=key)

    def insert(self, key, values):
        self.database[key] = values

        return values

    def update(self, key, **kwargs):

        values = self.database.data(key=key)

        for parameter in kwargs:
            values[parameter] = kwargs[parameter]

        self.database[key] = values

        return values

    def keys(self):
        return list(self.database[0].keys())

    def get_random(self):
        statement = random.choice(self.keys())
        return {statement: self.find(statement)}

class MyCorpus(object):

    def __init__(self):
        self.storage = []
        storage = JsonDatabase('database.db')

    def __iter__(self):
        storage = JsonDatabase('database.db')
        self.storage = storage.keys()
        for i in self.storage:
            goal = deleteStopwords(i)
            yield jieba.cut(goal)

class Markov(object):
    
    def __init__(self):
        self.storage = JsonDatabase('database.db')
        print('done responses')
        self.cache = {}
        self.words = []
        for r in self.storage.keys():
            database_values = self.storage.find(r)
            for i in database_values['response']:
                sentence = list(jieba.cut(i))
                self.words.extend(sentence)
        self.word_size = len(self.words)
        print('done words')
        self.database()
        print('done db')
    
    def triples(self):
        
        if len(self.words) < 3:
            return
        
        for i in range(len(self.words) - 2):
            yield (self.words[i], self.words[i+1], self.words[i+2])
            
    def database(self):
        for w1, w2, w3 in self.triples():
            key = (w1, w2)
            if key in self.cache:
                self.cache[key].append(w3)
            else:
                self.cache[key] = [w3]
                
    def generate_markov_text(self, seed, next):
        w1, w2 = seed, next
        gen_words = [seed, next]
        flag = True
        while flag:
            try:
                w1, w2 = w2, random.choice(self.cache[(w1, w2)])
            except KeyError:
                flag = False
            else:
                gen_words.append(w2)
            if u'。' in w2 or u'？' in w2 or u'！' in w2:
                flag = False
        return ''.join(gen_words)

class ChatBot(object):

    def __init__(self, name,
            database="database.db", logging=True):

        print(u'初始化中...')
        markov = input('喜欢我口若悬河吗？y/n:\n')
        if markov == 'y':
            self.speaking_mode = 'markov'
        else:
            self.speaking_mode = 'matching'

        self.name = name
        self.log = logging

        self.storage = JsonDatabase(database)

        self.recent_statements = []

        self.posts = processPosts()

        self.Corp = MyCorpus()
        print(u'语料载入完成！')
        self.dictionary = corpora.Dictionary(self.Corp)

        def dumpCorpus(Corp, dictionary):
            for text in Corp:
                yield dictionary.doc2bow(text)

        self.tfidf = models.TfidfModel(dumpCorpus(self.Corp, self.dictionary))

        self.corpus_tfidf = self.tfidf[list(dumpCorpus(self.Corp, self.dictionary))]
        print(u'tfidf模型载入完成！')
        if self.speaking_mode == 'markov':
            self.markov = Markov()
            print(u'Markov模型载入完成！')

        print(u'初始化完成！')

    def closest(self, query, database):

        vec_bow = self.dictionary.doc2bow(jieba.cut((query)))
        vec_tfidf = self.tfidf[vec_bow]
        index = similarities.MatrixSimilarity(self.corpus_tfidf)
        sims = index[vec_tfidf]
        target = sorted(enumerate(sims), key=lambda item: -item[1])[0]
        return self.Corp.storage[target[0]]

    def get(self, input_statement):

        closest_statement = self.closest(input_statement, self.storage)

        value = self.storage.find(closest_statement)
        if 'response' in value and value['response']:
            if self.speaking_mode == 'markov':
                potential = list(jieba.cut(random.choice(value['response'])))
                if len(potential) >= 2:
                    seed = potential[0]
                    next = potential[1]
                    matching_response = self.markov.generate_markov_text(seed, next)
                else:
                    matching_response = random.choice(self.storage.find(closest_statement)['response'])
            else:
                matching_response = random.choice(self.storage.find(closest_statement)['response'])
        else:
            matching_response = list(self.storage.get_random().keys())[0]

        return {matching_response: self.storage.find(matching_response)}

    def get_last_statement(self):
        if len(self.recent_statements) == 0:
            return None

        return self.recent_statements[-1]

    def timestamp(self, fmt="%Y-%m-%d-%H-%M-%S"):
        import datetime
        return datetime.datetime.now().strftime(fmt)

    def train(self, conversation): #beta
        for statement in conversation:

            if not self.storage.find(statement):
                self.storage.insert(statement, {})

            self.storage.update(statement, date=self.timestamp())

            responses = []
            database_values = self.storage.find(statement)

            if "response" in database_values:
                responses = database_values["response"]
                if conversation[-1] == statement:
                    responses = []
                else:
                    responses.append(conversation[conversation.index(statement) + 1])
            else:
                if conversation[-1] == statement:
                    responses = []
                else:
                    responses = [conversation[conversation.index(statement) + 1]]
            self.storage.update(statement, response=responses)

    def update_log(self, data):
        if self.get_last_statement():
            entry = list(self.get_last_statement().keys())[0]
            statement = list(data.keys())[0]
            values = data[statement]

            if not self.storage.find(entry):
                self.storage.insert(entry, {})

            self.storage.update(entry, name=values["name"], date=values["date"])

            responses = []

            database_values = self.storage.find(entry)

            if "response" in database_values:
                responses = database_values["response"]
                if statement not in responses:
                    responses.append(statement)
            else:
                responses = [statement]

            self.storage.update(entry, response=responses)

    def get_response_data(self, user_name, input_text):

        if input_text:
            response_statement = self.get(input_text)
        else:
            response_statement = self.storage.get_random()

        user = {
            input_text: {
                "name": user_name,
                "date": self.timestamp()
            }
        }

        if self.log:
            self.update_log(user)

        self.recent_statements.append(response_statement)
        statement_text = list(self.get_last_statement().keys())[0]

        return {user_name: user, "bot": statement_text}

    def get_response(self, input_text, user_name="HW"):

        response = self.get_response_data(user_name, input_text)["bot"]

        return response

# def tokenize(sentence):
#     return jieba.cut(sentence, cut_all=False)

# def score(sentence, target):
#     if sentence == target:
#         return sentence, 100
#     count = 0
#     l1 = list(tokenize(sentence))
#     l2 = list(tokenize(target))
#     base = len(l2) if len(l2) >= len(l1) else len(l1)
#     for w in l1:
#         if w in l2:
#             count += 1
#             l2.remove(w)
#     score = count/base
#     return sentence, round(score*100,1)

# def score2(sentence, target):
#     if sentence == target:
#         return sentence, 100
#     count = 0
#     for w in tokenize(sentence):
#         if w in tokenize(target):
#             count += 1
#     score = count/len(list(tokenize(target)))
#     return sentence, round(score*100,1)

# def extract(sentence, choices):
#     final = 'None', 0
#     for c in choices:
#         if final[1] < score(sentence, c)[1]:
#             final = c, score(sentence, c)[1]
#     return final[0]
        
if __name__ == '__main__':

    chatbot = ChatBot("cleverboy")

    # conversation = [
    #     u"你好",
    #     u"吃过早饭了吗？",
    #     u"吃过了",
    #     u"好吃吗？",
    #     u"棒极了"
    # ]

    # chatbot.train(conversation)

    flag = True

    while flag:
        st = input()
        if st == "end":
            flag = False
        else:
            response = chatbot.get_response(st)
            print(response)


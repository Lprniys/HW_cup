#coding=utf-8 

from __future__ import division
import random
from jsondb.db import Database
import jieba
from create import*

class JsonDatabaseAdapter:

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
        # The return value has to be cast as a list for Python 3 compatibility
        return list(self.database[0].keys())

    def get_random(self):
        """
        Returns a random statement from the database
        """
        statement = random.choice(self.keys())
        return {statement: self.find(statement)}

class MyCorpus(object):

    def __init__(self):
        self.storage = []
        storage = JsonDatabaseAdapter('database.db')

    def __iter__(self):
        storage = JsonDatabaseAdapter('database.db')
        self.storage = storage.keys()
        for i in self.storage:
            goal = deleteStopwords(i)
            yield jieba.cut(goal)

class Markov(object):
    
    def __init__(self):
        self.storage = JsonDatabaseAdapter('database.db')
        print('done responses')
        self.cache = {}
        self.words = []
        for r in self.storage.keys():
            database_values = self.storage.find(r)
            for i in database_values['response']:
                sentence = list(jieba.cut(i))
                # sentence[-1] += '。'
                self.words.extend(sentence)
        self.word_size = len(self.words)
        print('done words')
        self.database()
        print('done db')
    
    def triples(self):
        """ Generates triples from the given data string. So if our string were
                "What a lovely day", we'd generate (What, a, lovely) and then
                (a, lovely, day).
        """
        
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
            w1, w2 = w2, random.choice(self.cache[(w1, w2)])
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

        self.storage = JsonDatabaseAdapter(database)

        self.recent_statements = []

        self.posts = processPosts()
        # self.responses = processResponses()
        # self.conversation = processPair()

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

        # Check if an exact match exists
        # if database.find(text):
        #     return text

        # Get the closest matching statement from the database
        # return process.extract(text, database.keys(), limit=1)[0][0]
        vec_bow = self.dictionary.doc2bow(jieba.cut((query)))
        vec_tfidf = self.tfidf[vec_bow]
        index = similarities.MatrixSimilarity(self.corpus_tfidf)
        sims = index[vec_tfidf]
        target = sorted(enumerate(sims), key=lambda item: -item[1])[0]
        return self.Corp.storage[target[0]]

    def get(self, input_statement):

        closest_statement = self.closest(input_statement, self.storage)

        # Initialize
        value = self.storage.find(closest_statement)
        if 'response' in value and value['response']:
            if self.speaking_mode == 'markov':
                potential = list(jieba.cut(random.choice(value['response'])))
                seed = potential[0]
                next = potential[1]
                matching_response = self.markov.generate_markov_text(seed, next)
            else:
                matching_response = random.choice(self.storage.find(closest_statement)['response'])
        else:
            matching_response = list(self.storage.get_random().keys())[0]

        return {matching_response: self.storage.find(matching_response)}

    def get_last_statement(self):
        """
        Returns the last statement that was issued to the chat bot.
        """

        # If there was no last statements, return None
        if len(self.recent_statements) == 0:
            return None

        return self.recent_statements[-1]

    def timestamp(self, fmt="%Y-%m-%d-%H-%M-%S"):
        """
        Returns a string formatted timestamp of the current time.
        """
        import datetime
        return datetime.datetime.now().strftime(fmt)

    def train(self, conversation):
        for statement in conversation:

            database_values = self.storage.find(statement)

            # Create an entry if the statement does not exist in the database
            if not database_values:
                self.storage.insert(statement, {})

            self.storage.update(statement, date=self.timestamp())

            responses = []
            database_values = self.storage.find(statement)
            if "response" in database_values:
                responses = database_values["response"]
            if self.get_last_statement():
            # Check to make sure that the statement does not already exist
                if not self.get_last_statement() in responses:
                    responses.append(statement)

            if conversation[0] == statement:
                self.storage.update(statement, response=responses)
            else:
                self.storage.update(self.get_last_statement(), response=responses)
            
            self.recent_statements.append(statement)

    def update_log(self, data):
        if self.get_last_statement():
            entry = list(self.get_last_statement().keys())[0]
            statement = list(data.keys())[0]
            values = data[statement]

            # Create the statement if it doesn't exist in the database
            if not self.storage.find(entry):
                self.storage.insert(entry, {})

            # Update the database with the changes
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
        """
        Returns a dictionary containing the following data:
        * user: The user's statement meta data
        * bot: The bot's statement meta data
        """

        if input_text:
            response_statement = self.get(input_text)
        else:
            # If the input is blank, return a random statement
            response_statement = self.storage.get_random()

        user = {
            input_text: {
                "name": user_name,
                "date": self.timestamp()
            }
        }

        # Update the database before selecting a response if logging is enabled
        if self.log:
            self.update_log(user)

        self.recent_statements.append(response_statement)
        statement_text = list(self.get_last_statement().keys())[0]

        return {user_name: user, "bot": statement_text}

    def get_response(self, input_text, user_name="user"):

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

    flag = True

    while flag:
        st = input()
        if st == "end":
            flag = False
        else:
            response = chatbot.get_response(st)
            print(response)


import logging
import timeit
import sys
import string
import re

from mongoengine import connect, Document, StringField, DictField, FileField
from datetime import datetime
from pycoshark.mongomodels import VCSSystem, IssueSystem, IssueComment, Issue, MailingList, Message
from pycoshark.utils import create_mongodb_uri_string
from pycoshark.utils import get_base_argparser

from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from gensim import corpora, models
import gensim
import pyLDAvis.gensim


logger = logging.getLogger("main")

class TopicModel(Document):
    meta = {
        'indexes': [
            '#project_id'
        ],
        'shard_key': ('project_id', ),
    }
    project_id = StringField()
    config = DictField()
    view = FileField()
    dic = FileField()
    corpus = FileField()
    corpus_index = FileField()
    lda = FileField()
    lda_id2word = FileField()
    lda_state = FileField()
    lda_expElogbeta = FileField()
    

class topicSHARK(object):
    
    stopwords = set(stopwords.words('english'))
    punctuation = set(string.punctuation) 
    lemmatize = WordNetLemmatizer()
    
    
    whitelist = set("abcdefghijklmnopqrstuvwxy ABCDEFGHIJKLMNOPQRSTUVWXYZ?.!'")
    
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
            
    def configure(self, config):
        self._config = config
        text_file = open(config["filter"], "r")
        self.wordfilter = text_file.read().split(',')
        if 'language_filter' in config and config["language_filter"] != None:
            text_file2 = open(config["language_filter"])
            self.language_filter = text_file2.read().split(',')
        if 'project_filter' in config and config["project_filter"] != None:
            text_file3 = open(config["project_filter"])
            self.project_filter = text_file3.read().split(',')
        # Default values    
        if 'issue_comments' not in config or config["issue_comments"] == None:
            self._config['issue_comments'] = 'true'
        if 'issues' not in config or config["issues"] == None:
            self._config['issues'] = 'true'
        if 'messages' not in config or config["messages"] == None:
            self._config['messages'] = 'false'
        if 'passes' not in config or config["passes"] == None:
            self._config['passes'] = 20    
    def start(self):
        logger.info('Start: Data-Collection')
        # Collect data from DB
        docs = []
        if self._config['issues'] == 'true':
            logger.info('Start: Data-Collection for Issue Tracking Systems')
            for m in IssueSystem.objects.filter(project_id=self._config['project_id']):
                logger.info('Found Issue Tracking System:' + m.url)
                docs.extend(self.collectForIssueSystem(m));
            logger.info('Finish: Data-Collection for Issue Tracking Systems')
        
        if self._config['messages'] == 'true':
            logger.info('Start: Data-Collection for Messages')
            for m in MailingList.objects.filter(project_id=self._config['project_id']):
                logger.info('Found Mailling List:' + m.name)
                docs.extend(self.collectForMailingList(m))
            logger.info('Finish: Data-Collection for Messages')
        logger.info('Finish: Data-Collection')
        
            
        ### Topic Model
        # turn our tokenized documents into a id <-> term dictionary
        dictionary = corpora.Dictionary(docs)
        
        # convert tokenized documents into a document-term matrix
        corpus = [dictionary.doc2bow(text) for text in docs]
        
        # generate LDA model
        ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics=self._config["K"], id2word = dictionary, passes=self._config["passes"])
        #hdpmodel = gensim.m_logodels.hdpmodel.HdpModel(corpus,dictionary);
        #ldamodel = hdpmodel.suggested_lda_model();
        
     
        self.save(dictionary,corpus,ldamodel);
        return ldamodel;
    
    def collectForIssueSystem(self, issuesystem):
        docs = []
        for issue in Issue.objects.filter(issue_system_id=issuesystem.id):
            s = str(issue.title) + " " + str(issue.desc)
            if self._config['issue_comments'] == 'true':
                for issue_comment in IssueComment.objects.filter(issue_id=issue.id):
                    s += str(issue_comment.comment)
            s = self.cleaning(s);
            docs.append(s)
        # print(docs)
        return docs;
    
    def collectForMailingList(self, mailingList):
        docs = []
        for message in Message.objects.filter(mailing_list_id=mailingList.id):
            s = str(message.subject) + " " + str(message.body)
            s = self.cleaning(s)
            docs.append(s);
        # print(docs)
        return docs;

    def save(self,dic,corpus,model):
        prefix = self.getPrefix();            
        dic.save(prefix + '_dictionary.dict')
        corpora.MmCorpus.serialize(prefix + '_corpus.mm', corpus)
        model.save(prefix + '_topic.model')
        data = pyLDAvis.gensim.prepare(model, corpus, dic)
        pyLDAvis.save_json(data, prefix + '_view.data')
    
    def uploadToGridFS(self):
        logger.info("Delete old data form database")
        # Delete old models in database with same configuration
        for oldmodel in TopicModel.objects.filter(config=self._config):
            oldmodel.delete()

        prefix = self.getPrefix()
        config_db = { 'K' : self._config['K'],
              'filter' : self._config['filter'],
              'language_filter' : self._config['language_filter'],
              'project_filter' :  self._config['project_filter'],
              'issue_comments' :  self._config['issue_comments'],
              'issues' : self._config['issues'],
              'messages' : self._config['messages'],
              'passes' : self._config['passes']}  
        dbModel = TopicModel(project_id=self._config['project_id'], config=config_db)
        # Upload Dic
        dbModel.dic.put(open(prefix + '_dictionary.dict', 'rb'))
        # Upload corpus
        dbModel.corpus.put(open(prefix + '_corpus.mm', 'rb'))
        dbModel.corpus_index.put(open(prefix + '_corpus.mm.index', 'rb'))
        # Upload LDA Model
        dbModel.lda.put(open(prefix + '_topic.model', 'rb'))
        dbModel.lda_id2word.put(open(prefix + '_topic.model.id2word', 'rb'))
        dbModel.lda_state.put(open(prefix + '_topic.model.state', 'rb'))
        dbModel.lda_expElogbeta.put(open(prefix + '_topic.model.expElogbeta.npy', 'rb'))
        # Upload View Data
        dbModel.view.put(open(prefix + '_view.data', 'rb'))
        dbModel.last_updated = datetime.now()
        dbModel.save()
        logger.info("Saved all data to the database")

    def load(self):
        prefix = self.getPrefix();
        dic = gensim.corpora.Dictionary.load(prefix + '_dictionary.dict')
        corpus = gensim.corpora.MmCorpus(prefix + '_corpus.mm')
        lda = gensim.models.LdaModel.load(prefix + '_topic.model')
        return dic,corpus,lda;
        
    def getPrefix(self):
        prefix = self._config['output'] + "/"
        prefix += self._config['product_name']
        if self._config['issues'] == 'true':
            prefix += "_issues";
            if self._config['issue_comments'] == 'true':
                prefix += "_withComments";
        if self._config['messages'] == 'true':
            prefix += "_messages";
        return prefix;
    
    def pre_new(self, dictionary, newdoc):
        one = c.cleaning(newdoc)
        two = dictionary.doc2bow(one)
        return two
    
    def cleaning(self,article):
        # Remove URLS
        article = re.sub(r'^https?:\/\/.*[\r\n]*', '', article, flags=re.MULTILINE);
        article = article.replace('\r\n',' ');
        article = article.replace('\n',' ');
        # Only words..
        article = ''.join(filter(self.whitelist.__contains__, article));
        # Rest
        one = " ".join([i for i in article.lower().split() if i not in self.stopwords])  
        two = " ".join(self.lemmatize.lemmatize(i) for i in one.split())  
        three = "".join(i for i in two if i not in self.punctuation)
        # Words with size 2 or less makes no sense
        three = " ".join([w for w in three.split() if len(w)>2])
        ### Wordfilter
        three = " ".join([w for w in three.split() if not w in self.wordfilter])
        if hasattr(self,'language_filter'):
            three = " ".join([w for w in three.split() if not w in self.language_filter])
        if hasattr(self,'project_filter'):
            three = " ".join([w for w in three.split() if not w in self.project_filter])
        ###
        three = three.split();
        return three

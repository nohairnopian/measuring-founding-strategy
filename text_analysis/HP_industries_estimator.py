from gensim.parsing.preprocessing import remove_stopwords, preprocess_string, preprocess_documents
from sklearn.metrics.pairwise import linear_kernel
import pandas as pd
from sklearn.feature_extraction import text
from sklearn.feature_extraction.text import TfidfVectorizer
from website_text import website_text
import pdb
import pickle
import numpy as np
from sklearn.cluster import KMeans
from gensim.models import Word2Vec 
from gensim.models.doc2vec import Doc2Vec , TaggedDocument
import nltk
 
class HP_industries_estimator:

    def __init__(self):
        pass

    def train(self):
        self.train_tfidf()
        self.train_word2vec()

        
    def train_tfidf(self):
        if self.train_documents is None:
            self.prepare_train_documents()
            

        print("\t. Estimating similarity through tf-idf")
        print("\t. Creating TfidfVectorizer")
        #Update: many more ngrams allows
        vectorizer = TfidfVectorizer( decode_error = 'ignore',
                                      strip_accents = 'unicode',
                                      lowercase = True,
                                      stop_words = text.ENGLISH_STOP_WORDS,
                                      ngram_range = (1,3),
                                      max_df = .5,
                                      min_df = .005)
        print("\t. fit_transform")

        tfidf = vectorizer.fit_transform(self.train_documents)
        
        print("\t. Done")
        self.tfidf_model = tfidf



        
    def train_word2vec(self):
        if self.train_documents is None:
            self.prepare_train_documents()

        print("\t. Estimating Word2Vec model")            
        
        print("\t. Loading training documents")

        counter = 0
        all_docs = []
        for train_doc in self.train_documents:

            doc = train_doc[:150000] if len(train_doc) > 150000 else train_doc
            if (counter%100) == 0:
                print("{0} .. len: {1}".format(counter,len(doc)))

            counter += 1
            doc = remove_stopwords(doc)
#            doc = re.sub(r'[^\w\s]','',doc)
            doc_tokens =nltk.word_tokenize(doc.lower())
            all_docs.append(doc_tokens)            

        print("Creating all tagged documents")
        documents = [TaggedDocument(doc, [i]) for i, doc in enumerate(all_docs)]    

        print("\t. Run model")
        model = Doc2Vec(documents = documents)
        print("\t. Done")
        self.word2vec_model = model
    
    

    def store_model(self, path):
        print ("Storing tf idf model to {0}".format(path))
        pickle.dump(self.tfidf_model , open(path + ".model.pickle","wb"))
        self.website_info.to_pickle(path + ".website_info.pickle")
        self.word2vec_model.save(path + ".word2vec.model")



    def load_model(self, path):
        print("\t.Loading from {0}".format(path))
        self.tfidf_model = pickle.load(open(path + ".model.pickle","rb"))
        self.website_info = pd.read_pickle(path + ".website_info.pickle")
        self.word2vec_model = Word2Vec.load(path + ".word2vec.model")




    def estimate_industries(self):
        ### TF IDF HP Industries: The approach by HP
        print("\t.Estimating linear kernel similarity")
        sim = linear_kernel(self.tfidf_model, self.tfidf_model)
        print("\t.Done")

        print("\t.Estimating KMeans clustering for firms")
        kmeans = KMeans(n_clusters = 300 , random_state = 12345).fit(sim)
        print("\t.Done")

        hp_industries =  kmeans.labels_
        print("\t. Updating website")
        self.website_info["hp_industry"] =  hp_industries


        ### Word2Vec HP Industries: The approach by HP but using w2v similarity
        print("\t.Initializing Word2Vec Matrices")
        self.word2vec_model.init_sims()
        print("\t.Estimating Word2Vec Similarity")
        mat = self.word2vec_model.docvecs.doctag_syn0norm
        w2v_sim = np.dot(mat, mat.T)
        kmeans = KMeans(n_clusters = 300 , random_state = 12345).fit(w2v_sim)
        print("\t.Done")

        
        hp_industries =  kmeans.labels_
        print("\t. Updating website info")
        self.website_info["w2v_hp_industry"] =  hp_industries
        
            




    def prepare_train_documents(self):
        documents = []
        
        for w in self.websites:
            text = w.get_website_text()
            text = text[:400000] if len(text) > 400000 else text
            documents.append(text)

        self.train_documents = documents



    def load_train(self, website_df):
        websites = []
        
        website_list= []

        print("Loading all websites. Total: {0}".format(website_df.shape[0]))
        counter  = 0
        counter_good = 0
        for index , row in website_df.iterrows():
            counter += 1
            doc = website_text(row['path'], row['website'] , row['year'], row['incyear'], skip_memory_error=True)

            if doc is not None and doc.is_valid_website():
                counter_good += 1
                websites.append(doc)

                website_info = {}
                website_info['website'] = row['website']
                website_info['text_len'] = len(doc.get_website_text())
                website_info['source'] = row['source']

                text = doc.get_website_text()
                text = text[1:600] if len(text) > 600 else text
                website_info['text'] = text

                website_info['type'] = row['type']                                
                website_list.append(website_info)

            if (counter % 10) == 0:
                print("\t.. {0} ({1})".format(counter, counter_good))

        self.website_info = pd.DataFrame(website_list)    
        self.websites = websites
        print("\t Done")
        


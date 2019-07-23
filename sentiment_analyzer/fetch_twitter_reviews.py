from __future__ import print_function
from base import Base
import base
from Queue import Queue
import csv
import time
import json
from datetime import datetime
import sys, traceback
import re


folder = 'dataset_part2/'

class Tweet(object):
    def __init__(self, raw_tweet=None):
        self.tweet = raw_tweet
        self.tweet_as_row = []
        self.last_id = None

    def parse_tweet(self):
        """
        @return: [created_at, text,
                  sentiment, rating, source]
        """

        try:

            fields = ["created_at", "text"]
            for f in fields:
                self.tweet_as_row.append(str(self.tweet[f].encode('utf-8')))

            self.tweet_as_row.append("") # Sentiment
            self.tweet_as_row.append("") # Rating
            self.tweet_as_row.append("Twitter") # Source

            return self.tweet_as_row

        except UnicodeEncodeError as e:
            print(e, self.tweet[f])

    def get_tweet_id(self):
        if self.tweet is None:
            return None
        return self.tweet["id_str"]

    def get_location(self):
        if self.tweet_as_row is None:
            return None
        return self.tweet_as_row[4]

def get_last_marker():
    with open('tweet_marker.json', 'r') as f:
        data = json.load(f)
    return data

def save_last_marker(max_id="", page=1, store_key=None):
    marker_data = {"max_id":max_id, "page":page, "store_key":store_key}
    with open('tweet_marker.json', 'w') as f:
        json.dump(marker_data, f)

def setup_client():
    client = Base()
    creds = client.load_config("Twitter")
    return client.authenticate(creds)

def get_stores():
    stores = {
    "Dallas1":["32.776664","-96.796988", "208 S Akard Street, Ste 110", "75202"],
    "Dallas2":["32.8111091","-96.8092962","3329 Oak Lawn Avenue", "75219"],
    "Dallas3":["32.8293128","-96.8272358","5616 Lemmon Ave","75209"],
    "Dallas4":["32.8685017","-96.7757012","8687 N Central Expressway Suite 2340", "75225"],
    "Dallas5":["32.8342578","-96.7045404","1152 North Buckner Blvd", "75218"],
    "Dallas6":["32.8740567","-96.771404","9100 N Central Expressway Suite 105", "75231"],
    "Dallas7":["32.8957338","-96.8079243","5959 Royal Lane", "75230"],
    "Dallas8":["32.913273","-96.958064","7800 N. Macarthur Boulevard Suite 150", "75063"],
    "Dallas9":["33.009892","-96.709061","701 N Central Expy", "75075"],
    "Dallas10":["32.953929","-96.821254","5100 Beltline Road Ste. 1032", "75254"],
    "Dallas11":["32.934372","-96.820672","13710 Dallas Parkway Suite I", "75240"],
    "Dallas12": ["32.836504", "-96.771185", "5618 E Mockingbird Lane", "75206"],
    "Dallas13": ["32.845283", "-96.787396", "6417 Hillcrest Ave","75205"],
    "Dallas14": ["32.853358", "-96.817694", "5567 W Lovers Ln","75209"],
    "Dallas15": ["32.853965", "-96.769903", "5521 Greenville Ave", "75206"],
    "Dallas16": ["32.865482", "-96.805688", "5960 W Northwest Hwy", "75225"],
    "Dallas17": ["32.739229", "-96.682466", "1530 S Buckner Blvd", "75217"],
    "Dallas18": ["32.980547", "-96.767442", "2160 N Coit Rd Ste 141", "75080"]
    }
    return stores

def fetch_store_data(store_key):
    stores = get_stores()
    return stores[store_key]

def num_stores():
    return len(get_stores())

def pause_processing(start_time, minutes=16):
    time_gap = 60*minutes
    end_time = datetime.now()
    difference = end_time - start_time
    delta = difference.seconds
    print("Program sleeping for %s mins after %s" % (minutes, start_time))
    time.sleep(time_gap - delta)

def main():
    try:
        consumer = setup_client()
        start_time = datetime.now()
        print("Start time of run %s " % str(start_time))

        store_list = []
        for idx in range(num_stores()):
            store_list.append("Dallas"+str(idx+1))

        page = 1
        api_calls = 1
        tweet_queue = Queue()
        last_result = get_last_marker()
        idx = 0

        max_id, page = last_result["max_id"], last_result["page"]
        last_store = last_result["store_key"]
        store_idx = int(re.findall("[0-9]+", last_store)[0])
        if store_idx != 0:
            idx = store_idx-1

        queries = [
        'att%20OR%20attcares%20OR%20uverse%20OR%20attfiber%20OR%20directv%20OR%20directvservice',
        '%40att%20OR%20%40attcares%20OR%20%40uverse%20OR%20%40directv%20OR%20%40directvservice',
        '%23att%20OR%20%23attcares%20OR%20%23uverse%20OR%20%23directv%20OR%20%23attfiber'
        ]

        for store in store_list[idx:]:

            # Loop through feed
            while page <= 50:
                store_data = fetch_store_data(store)
                loc = store_data[0] + ',' + store_data[1]
                query = queries[2]+'&geocode='+loc+',7mi&count=100'
                raw_tweets = base.fetch_twitter_feed(consumer, loc, max_id, query)

                if raw_tweets is None or raw_tweets == []:
                    print("Breaking from empty raw_tweets")
                    break


                if api_calls > 175:
                    pause_processing(start_time, minutes=16)
                    api_calls = 1
                    start_time = datetime.now()

                for tweet in raw_tweets:
                    T = Tweet(tweet)
                    processed_tweet = T.parse_tweet()

                    # Skip the last processed tweet
                    if max_id == T.get_tweet_id():
                        continue

                    tweet_queue.put(processed_tweet)
                    max_id = T.get_tweet_id()

                filename = folder+store+'_twitter_'+str(page)+'.csv'
                write_headers_flag = True
                f = open(filename, 'a')
                writer = csv.writer(f)


                # Open file and write line by line
                while not tweet_queue.empty():
                    if write_headers_flag == False:

                        # Set headers of the file (columns)
                        writer.writerow(('Store', 'Latitude', 'Longitude',
                                         'Address', 'Zip','CreatedAt', 'Text',
                                         'Senti', 'Rating', 'Source'))
                        write_headers_flag = True

                    current_tweet = tweet_queue.get()
                    writer.writerow((store, store_data[0],
                                    store_data[1], store_data[2],
                                    store_data[3], current_tweet[0],
                                    current_tweet[1], current_tweet[2],
                                    current_tweet[3], current_tweet[4]))

                f.close()

                # Save marker to file
                save_last_marker(max_id, page, store)

                print("Page %s with reviews %s processed for store %s" % (page, len(raw_tweets), store))

                # Rate limit the calls to Twitter
                page += 1
                api_calls += 1

            page = 1
            max_id = ""


    except Exception as e:
        print(e)
        traceback.print_exc()


if __name__ == '__main__':
    main()

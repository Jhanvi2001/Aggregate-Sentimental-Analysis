# -*- coding: utf-8 -*-
"""
Created on Tue Jun 22 11:46:28 2021

@author: sjhan
"""

import argparse
import os
import json
import pandas as pd
import googleapiclient.discovery
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import nltk
from youtube_transcript_api import YouTubeTranscriptApi
from pprint import pprint
import warnings
warnings.filterwarnings("ignore")
analyser = SentimentIntensityAnalyzer()

# Function to classify a sentence into one of the 3 sentiments : Positive, Negative or Neutral


def sentiment_scores(sentence):
    snt = analyser.polarity_scores(sentence)
    if snt['compound'] >= 0.05:
        return 'Positive'
    elif snt['compound'] <= -0.05:
        return 'Negative'
    else:
        return 'Neutral'


def retrieve_transcript(video_id):
    output = YouTubeTranscriptApi.get_transcript(video_id)
    segments = []
    for e in output:
        line = e['text']
        line = line.replace('\n', '')
        line = line.replace('>', '')
        line = line.replace('--', '')
        line = line.replace('♪', '')
        segments.append(line)

    transcript = " ".join(segments)
    return transcript,segments


def json_parser(json_response):
    comments = []
    likes = []
    replies = []
    for item in json_response.get('items'):
        comments.append(item.get('snippet').get(
            'topLevelComment').get('snippet')['textOriginal'])
        likes.append(item.get('snippet').get(
            'topLevelComment').get('snippet')['likeCount'])
        replies.append(item.get('snippet')['totalReplyCount'])

    assert len(comments) == len(likes) == len(replies), 'Length not matching'

    df = pd.DataFrame()
    df['Comments'] = comments
    df['Likes'] = likes
    df['Replies'] = replies

    return df

# Function to scrape comments, their number likes and number replies using YouTube V3 API - NEEDS DEVELOPER_KEY

def comment_scraper(video_id, max_comments, file_name):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = "AIzaSyDEyoZhTj3wh0B3r3evEmIxI-4g2Aa9-dE"

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    request = youtube.commentThreads().list(
        part="snippet,replies",
        maxResults=max_comments,
        order="relevance",
        videoId=video_id
    )
    response = request.execute()

    comment_df = json_parser(response)
    comment_df['Sentiment'] = comment_df['Comments'].apply(
        lambda x: sentiment_scores(x))

    with open(file_name, 'w') as f:
        json.dump(response, f)

    return comment_df

def transcript_scrapper(video_id):
    _,transcript = retrieve_transcript(video_id)
    transcript_df = pd.DataFrame()
    transcript_df['Transcript'] = transcript
    transcript_df['Sentiment'] = transcript_df['Transcript'].apply(lambda x: sentiment_scores(x))
    return transcript_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--id", type=str, default='JwSS70SZdyM',
                    help="Video ID for YouTube video.")
    ap.add_argument("-o", "--output", type=str, default='comment_sentiment.txt',
                    help="File to output response json results to.")
    ap.add_argument("-n", "--number", type=int, default=100,
                    help="Number of comments to scrape")
    args = vars(ap.parse_args())

    video_id = args['id']
    max_num = args['number']
    save_path = args['output']

    transcript_df = transcript_scrapper(video_id=video_id)
    
    neutral_trans = transcript_df[transcript_df['Sentiment'] == 'Neutral']['Transcript']
    negative_trans = transcript_df[transcript_df['Sentiment'] == 'Negative']['Transcript']
    positive_trans = transcript_df[transcript_df['Sentiment']== 'Positive']['Transcript']

    trans_len = len(neutral_trans)+len(negative_trans)+len(positive_trans)
    final_json_trans = dict({"positive": round(len(positive_trans)/trans_len, 3), "negative": round(len(negative_trans)/trans_len, 3), "neutral": round(len(neutral_trans)/trans_len, 3)})

    comment_df = comment_scraper(video_id=video_id, max_comments=max_num, file_name=save_path)
    neutral_comms = comment_df[comment_df['Sentiment']
                               == 'Neutral']['Comments']
    negative_comms = comment_df[comment_df['Sentiment']
                                == 'Negative']['Comments']
    positive_comments = comment_df[comment_df['Sentiment']
                                   == 'Positive']['Comments']

    comms_len = len(neutral_comms)+len(negative_comms)+len(positive_comments)
    final_json_comms = dict({"positive": round(len(positive_comments)/comms_len, 3), "negative": round(
        len(negative_comms)/comms_len, 3), "neutral": round(len(neutral_comms)/comms_len, 3)})

    output = {
        "Transcript": {},
        "Comments": {}
    }
    output["Transcript"] = final_json_trans
    output["Comments"] = final_json_comms
    pprint(output, indent=1, width=1, compact=False)
    
if __name__ == "__main__":
    main()
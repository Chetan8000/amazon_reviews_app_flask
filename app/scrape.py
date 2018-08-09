from lxml import html
import requests
import numpy as np
import pandas as pd
import os
from flask import Markup, flash


def scrape_reviews(asin):
    ratings_dict = {}
    reviews_list = []
    reviews_df = pd.DataFrame()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36'}
    XPATH_REVIEWS = '//div[@data-hook="review"]'
    XPATH_REVIEW_RATING = './/i[@data-hook="review-star-rating"]//text()'
    XPATH_REVIEW_HEADER = './/a[@data-hook="review-title"]//text()'
    XPATH_REVIEW_AUTHOR = './/a[@data-hook="review-author"]//text()'
    XPATH_REVIEW_DATE = './/span[@data-hook="review-date"]//text()'
    XPATH_REVIEW_BODY = './/span[@data-hook="review-body"]//text()'
    XPATH_REVIEW_HELPFUL = './/span[@data-hook="helpful-vote-statement"]//text()'
    XPATH_REVIEW_PAGENUM = './/li[@class="page-button"]//text()'
    XPATH_TOTAL_REVIEWS = './/span[@data-hook="total-review-count"]//text()'
    amazon_page1 = 'https://www.amazon.com/product-reviews/' + asin + '/ref=cm_cr_arp_d_paging_btm_1?pageNumber=1&sortBy=recent'

    p_num = 1
    page = requests.get(amazon_page1, headers=headers)
    page_response = page.text.encode('utf-8')
    parser = html.fromstring(page_response)
    pages = parser.xpath(XPATH_REVIEW_PAGENUM)
    totalreviews = parser.xpath(XPATH_TOTAL_REVIEWS)
    totalreviews = int(totalreviews[0].replace(",",""))
    maxpage = int(pages[-1].replace(",",""))
    totalpages = maxpage

    while True:
        # print('Scraping reviews on page {} out of total {} pages...'.format(p_num, totalpages))
        # progress_msg = 'Scraping reviews on page {} out of total {} pages...'.format(p_num, totalpages)
        #message = Markup("<h5> {{progress_msg}} </h5>")
        # flash(progress_msg)
        amazon_url = 'https://www.amazon.com/product-reviews/' + asin + '/ref=cm_cr_arp_d_paging_btm_' +str(p_num) + '?pageNumber=' + str(p_num) + '&sortBy=recent'
        # Add some recent user agent to prevent amazon from blocking the request
        # Find some chrome user agent strings  here https://udger.com/resources/ua-list/browser-detail?browser=Chrome
        page = requests.get(amazon_url, headers=headers)
        page_response = page.text.encode('utf-8')
        parser = html.fromstring(page_response)
        reviews = parser.xpath(XPATH_REVIEWS)

        if not len(reviews) > 0:
            break
        # Parsing individual reviews
        for review in reviews:
            raw_review_author = review.xpath(XPATH_REVIEW_AUTHOR)
            raw_review_rating = review.xpath(XPATH_REVIEW_RATING)
            raw_review_header = review.xpath(XPATH_REVIEW_HEADER)
            raw_review_date = review.xpath(XPATH_REVIEW_DATE)
            raw_review_body = review.xpath(XPATH_REVIEW_BODY)
            raw_review_helpful = review.xpath(XPATH_REVIEW_HELPFUL)

            review_dict = {
                'review_text': raw_review_body,
                'review_posted_date': raw_review_date,
                'review_header': raw_review_header,
                'review_rating': raw_review_rating,
                'review_helpful': raw_review_helpful,
                'review_author': raw_review_author
            }
            reviews_df = reviews_df.append(review_dict, ignore_index=True)
        p_num += 1
        if p_num > totalpages:
            break
            # convert list to string
    for col in reviews_df.columns:
        reviews_df[col] = reviews_df[col].apply(lambda x: '\n'.join(x))
    reviews_df['review_helpful'] = (reviews_df['review_helpful']
                                    .str.replace('One', '1')
                                    .str.replace(r'[^0-9]', ''))
    reviews_df['review_helpful'].loc[reviews_df['review_helpful'] == ''] = '0'
    reviews_df['review_helpful'] = reviews_df['review_helpful'].astype(int)
    reviews_df['review_posted_date'] = pd.to_datetime(reviews_df['review_posted_date']
                                                      .str.strip('on'))
    reviews_df['review_rating'] = reviews_df['review_rating'].str.strip('out of 5 stars').astype(float)
    reviews_df.loc[reviews_df['review_rating'] == 0, 'review_rating'] = 5
    reviews_df['review_length'] = reviews_df['review_text'].apply(lambda x: len(x))
    reviews_df.drop_duplicates(inplace=True)
    return reviews_df
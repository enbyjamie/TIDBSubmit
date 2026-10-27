import os
import requests
import json
from dotenv import load_dotenv


load_dotenv()

from filmObject import MediaObject

class introSubmitter:

    def __init__(self):
        self.INTRO_submit = "https://api.theintrodb.org/v4/submit"
        self.INTRO_APIKEY = os.getenv("INTRO_APIKEY")

        self.TMDB_search = "https://api.themoviedb.org/3/search"
        self.TMDB_APIKEY = os.getenv("TMDB_APIKEY")

    def searchForFilm(self, x):
        print("Searching for: " + x)
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.TMDB_APIKEY}"
        }

        parameters = {
            "query": x,
            "page": 1
        }

        response = requests.get(f"{self.TMDB_search}/movie?", headers=headers, params=parameters)
        response.raise_for_status()

        return self.parseResponse(response.json(), "movie")

    def searchForTV(self, x):
        print("Searching for: " + x)
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.TMDB_APIKEY}"
        }

        parameters = {
            "query": x,
            "page": 1
        }

        response = requests.get(f"{self.TMDB_search}/tv?", headers=headers, params=parameters)
        response.raise_for_status()

        return self.parseResponse(response.json(), "tv")

    @staticmethod
    def parseResponse(response, type):
        for subitem in response["results"]:
            if type == "movie":
                name = 'original_title'
                date = 'release_date'
            elif type == "tv":
                name = 'original_name'
                date = 'first_air_date'

            i = input(f"Are you looking for {subitem[name]}, released {subitem[date]} with a rating of {round(subitem['vote_average'], 1)}? [Y/n] ") or "y"

            if i.strip().lower() == 'y':
                # print(subitem['original_title'], subitem['release_date'],round(subitem['vote_average'], 1),subitem['overview'],subitem['id'])
                return MediaObject(
                    subitem[name],
                    subitem[date],
                    round(subitem['vote_average'], 1),
                    subitem['overview'],
                    subitem['id'],
                    type
                )
        return None

    def showInfo(self, mediaObject):
        """
        :param mediaObject: title, date, rating, synopsis, TMDBid
        """
        if mediaObject is not None:
            print(f"\n{self.starRating(mediaObject.rating)} | {mediaObject.title}, released {mediaObject.date}")
            print(f"{mediaObject.synopsis}")
            print(f"TMDBid: {mediaObject.TMDBid}")
            self.submitIntro(mediaObject)
        else:
            print("ruh roh")

    def starRating(self, rating):
        points = int(rating + 0.5)

        fullStars = points // 2
        halfStars = points % 2
        emptyStars = 5 - (fullStars + halfStars)

        stars = (' ' * fullStars) + (' ' * halfStars) + (' ' * emptyStars)

        return stars

    def submitIntro(self, mediaObject):
        if input(f"\nWould you like to submit an intro/credits skip for {mediaObject.title}? [Y/n] ") or "y".strip().lower() == 'y':
            segment = input("What kind of skip is it? [intro (default), recap, credits, preview] ") or "intro"

            if segment != "intro" and segment != "recap" and segment != "credits" and segment != "preview":
                print("That's not a valid type. Try again.")
                return

            print("For the following, press RETURN if it lasts from / to the start / end of the media.")
            startsecs = self.toSeconds(input("What is the start time? [HH:MM:SS] "))
            print(startsecs)
            endsecs = self.toSeconds(input("What is the end time? [HH:MM:SS] "))
            print(endsecs)

            #if not self.checkSegment(mediaObject.type, startsecs, endsecs): # ! TBD: fix logic
            #    print("That's not valid. Please check the TIDB docs and try again.")
            #    return

            if mediaObject.type == "tv":
                se = int(input("What season? "))
                ep = int(input("What episode? "))
                mapping = input("What episode mapping order? [default (default), official, dvd, alternate, absolute, regional] ") or None
                if mapping == "default":
                    mapping = None
                self.constructTIDBPostTV(mediaObject.TMDBid, mediaObject.type, se, ep, segment, startsecs, endsecs, mapping) # id, type, season, episode, segment, start, end, mapping
            elif mediaObject.type == "movie":
                self.constructTIDBPostFilm(mediaObject.TMDBid, mediaObject.type, segment, startsecs, endsecs) # id, type, segment, start, end

    def toSeconds(self, s):
        if s == '':
            return "null"

        l = list(map(int, s.split(':')))  # l = list(map(int, s.split(':'))) in Python 3.x
        return sum(n * sec for n, sec in zip(l[::-1], (1, 60, 3600)))

    def checkSegment(self, segmentType, start, end):
        '''if segmentType == "intro" or segmentType == "recap":
            if end == "null":
                print("err 0")
                return False
            if start != "null":
                if end - start > 21600:
                    print("err 1")
                    return False
                return True
            return True
        elif segmentType == "credits" or segmentType == "preview":
            if start == "null":
                print("err 2")
                return False
            if end != "null":
                if end - start > 21600:
                    print("err 3")
                    return False
                return True
            return True
        return None'''

    def constructTIDBPostTV(self, id, type, season, episode, segment, start, end, mapping=None):
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.INTRO_APIKEY}"
        }

        if start != "null": formattedStart = "{:.1f}".format(float(start))
        else: formattedStart = start

        if end != "null": formattedEnd = "{:.1f}".format(float(end))
        else: formattedEnd = end

        start_val = None if formattedStart == "null" else float(formattedStart)
        end_val = None if formattedEnd == "null" else float(formattedEnd)

        data = {
            "tmdb_id": id,
            "type": f"{type}",
            "season": season,
            "episode": episode,
            "segment": f"{segment}",
            "start_sec": start_val,
            "end_sec": end_val,
        }
        if mapping:
            data["mapping"] = mapping

        '''req = requests.Request('POST', self.INTRO_submit, headers=headers, json=data)
        prepared = req.prepare()

        print("json data")
        print(prepared.body.decode('utf-8'))

        print("\nheaders")
        for key, value in prepared.headers.items():
            print(f"{key}: {value}") '''

        response = requests.post(self.INTRO_submit, headers=headers, json=data)
        print("\nresponse")
        self.checkSubmission(response)

    def constructTIDBPostFilm(self, id, type, segment, start, end):
        print("TO BE WORKED ON")
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.INTRO_APIKEY}"
        }

        if start != "null": formattedStart = "{:.1f}".format(float(start))
        else: formattedStart = start

        if end != "null": formattedEnd = "{:.1f}".format(float(end))
        else: formattedEnd = end

        start_val = None if formattedStart == "null" else float(formattedStart)
        end_val = None if formattedEnd == "null" else float(formattedEnd)

        data = {
            "tmdb_id": id,
            "type": f"{type}",
            "segment": f"{segment}",
            "start_sec": start_val,
            "end_sec": end_val,
        }

        '''req = requests.Request('POST', self.INTRO_submit, headers=headers, json=data)
        prepared = req.prepare()

        print("json data")
        print(prepared.body.decode('utf-8'))

        print("\nheaders")
        for key, value in prepared.headers.items():
            print(f"{key}: {value}") '''

        response = requests.post(self.INTRO_submit, headers=headers, json=data)
        print("\nresponse")
        self.checkSubmission(response)

    def checkSubmission(self, response):
        if response.status_code == 200 and response.json().get('ok') is True:
            submission_json = response.json()
            print("Submitted successfully")
            for sub in submission_json.get('submissions', []):
                print(f"id: {sub['id']}")
                print(f"weight: {sub['weight']}")
                if 'tvdbId' in sub and sub['tvdbId'] is not None:
                    print(f"tvdbId: {sub['tvdbId']}")
        else:
            print(f"Submission failed with code {response.status_code}")
            print(response.text)

introsubmitter = introSubmitter()
x = input("Search for a film or show? ") or "show"
inp = input("Title? ")
if x.lower() == "film":
    introsubmitter.showInfo(introsubmitter.searchForFilm(inp))
else:
    introsubmitter.showInfo(introsubmitter.searchForTV("fionna and cake"))

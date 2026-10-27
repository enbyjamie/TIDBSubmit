import os
import sys
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

from filmObject import MediaObject


def update_env_file(key: str, value: str, env_path: str = ".env") -> None:
    """Update or add a key-value pair in .env file."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def prompt_for_key(key_name: str, description: str) -> str:
    """Prompt user for missing/invalid API key with optional .env persistence."""
    val = input(f"\nEnter your {description} ({key_name}): ").strip()
    if not val:
        print(f"Error: {key_name} cannot be empty.")
        sys.exit(1)
    persist = input(f"Save {key_name} to .env? [Y/n] ") or "y"
    if persist.strip().lower() == "y":
        update_env_file(key_name, val)
        print(f"Saved {key_name} to .env.")
    os.environ[key_name] = val
    return val


class introSubmitter:

    def __init__(self):
        self.INTRO_submit = "https://api.theintrodb.org/v4/submit"
        self.INTRO_APIKEY = os.getenv("INTRO_APIKEY")

        self.TMDB_search = "https://api.themoviedb.org/3/search"
        self.TMDB_APIKEY = os.getenv("TMDB_APIKEY")

    def search_tmdb(self, media_type: str, query: str) -> Optional[MediaObject]:
        print("Searching for: " + query)
        if not self.TMDB_APIKEY:
            self.TMDB_APIKEY = prompt_for_key("TMDB_APIKEY", "TMDB API Read Access Token")

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.TMDB_APIKEY}"
        }
        parameters = {
            "query": query,
            "page": 1
        }

        response = requests.get(f"{self.TMDB_search}/{media_type}", headers=headers, params=parameters)
        if response.status_code in (401, 403):
            print(f"\nAuthentication failed with TMDB ({response.status_code}).")
            self.TMDB_APIKEY = prompt_for_key("TMDB_APIKEY", "new TMDB API Read Access Token")
            headers["Authorization"] = f"Bearer {self.TMDB_APIKEY}"
            response = requests.get(f"{self.TMDB_search}/{media_type}", headers=headers, params=parameters)

        response.raise_for_status()
        return self.parseResponse(response.json(), media_type)

    def searchForFilm(self, x: str) -> Optional[MediaObject]:
        return self.search_tmdb("movie", x)

    def searchForTV(self, x: str) -> Optional[MediaObject]:
        return self.search_tmdb("tv", x)

    @staticmethod
    def parseResponse(response: dict, media_type: str) -> Optional[MediaObject]:
        for subitem in response.get("results", []):
            if media_type == "movie":
                name = 'original_title'
                date = 'release_date'
            elif media_type == "tv":
                name = 'original_name'
                date = 'first_air_date'
            else:
                continue

            title = subitem.get(name, "Unknown Title")
            rel_date = subitem.get(date, "Unknown Date")
            rating = round(subitem.get('vote_average', 0.0), 1)

            i = input(f"Are you looking for {title}, released {rel_date} with a rating of {rating}? [Y/n] ") or "y"
            if i.strip().lower() == 'y':
                return MediaObject(
                    title,
                    rel_date,
                    rating,
                    subitem.get('overview', ''),
                    subitem.get('id', 0),
                    media_type
                )
        return None

    def showInfo(self, mediaObject: Optional[MediaObject]) -> None:
        if mediaObject is not None:
            print(f"\n{self.starRating(mediaObject.rating)} | {mediaObject.title}, released {mediaObject.date}")
            print(f"{mediaObject.synopsis}")
            print(f"TMDBid: {mediaObject.TMDBid}")
            self.submitIntro(mediaObject)
        else:
            print("No matching media found.")

    @staticmethod
    def starRating(rating: float) -> str:
        points = int(rating + 0.5)
        fullStars = points // 2
        halfStars = points % 2
        emptyStars = 5 - (fullStars + halfStars)
        return (' ' * fullStars) + (' ' * halfStars) + (' ' * emptyStars)

    @staticmethod
    def toSeconds(s: str) -> Optional[float]:
        """Convert HH:MM:SS, MM:SS, or seconds string to float seconds. Returns None if empty."""
        s = s.strip()
        if not s:
            return None
        parts = s.split(':')
        try:
            numbers = [float(p) for p in parts]
            multipliers = [1, 60, 3600]
            if len(numbers) > len(multipliers):
                print(f"Invalid timestamp format '{s}'. Too many time components.")
                return None
            return sum(n * sec for n, sec in zip(reversed(numbers), multipliers))
        except ValueError:
            print(f"Invalid timestamp format '{s}'. Expected HH:MM:SS, MM:SS, or seconds.")
            return None

    @staticmethod
    def validate_segment(segment: str, start: Optional[float], end: Optional[float]) -> bool:
        """Validate timestamps according to TheIntroDB v4 business rules."""
        if segment not in ("intro", "recap", "credits", "preview"):
            print(f"Error: Invalid segment type '{segment}'. Must be intro, recap, credits, or preview.")
            return False

        for val, label in ((start, "Start time"), (end, "End time")):
            if val is not None:
                if val < 0:
                    print(f"Error: {label} cannot be negative.")
                    return False
                if val > 21600:
                    print(f"Error: {label} exceeds maximum allowed duration of 6 hours (21600s).")
                    return False

        # Explicit no-segment submission: both None or both 0
        if (start is None and end is None) or (start == 0 and end == 0):
            return True

        if segment in ("intro", "recap"):
            if end is None:
                print(f"Error: {segment.capitalize()} segment requires an end time.")
                return False
            effective_start = start if start is not None else 0.0
            if end < effective_start:
                print(f"Error: End time ({end}s) must be greater than start time ({effective_start}s).")
                return False
            duration = end - effective_start
            max_dur = 300.0 if segment == "intro" else 1200.0
            if duration > 0 and duration < 5.0:
                print(f"Error: {segment.capitalize()} duration must be at least 5 seconds.")
                return False
            if duration > max_dur:
                print(f"Error: {segment.capitalize()} duration ({duration:.1f}s) exceeds maximum of {int(max_dur)}s.")
                return False

        elif segment in ("credits", "preview"):
            if start is None:
                print(f"Error: {segment.capitalize()} segment requires a start time.")
                return False
            if end is not None:
                if end < start:
                    print(f"Error: End time ({end}s) must be greater than start time ({start}s).")
                    return False
                duration = end - start
                if duration > 0 and duration < 5.0:
                    print(f"Error: {segment.capitalize()} duration must be at least 5 seconds.")
                    return False
                if duration > 1800.0:
                    print(f"Error: {segment.capitalize()} duration ({duration:.1f}s) exceeds maximum of 1800s (30 mins).")
                    return False

        return True

    def submitIntro(self, mediaObject: MediaObject) -> None:
        confirm = input(f"\nWould you like to submit an intro/credits skip for {mediaObject.title}? [Y/n] ") or "y"
        if confirm.strip().lower() != 'y':
            return

        segment = input("What kind of skip is it? [intro (default), recap, credits, preview] ") or "intro"
        if segment not in ("intro", "recap", "credits", "preview"):
            print("That's not a valid type. Try again.")
            return

        print("For the following, press RETURN if it lasts from / to the start / end of the media.")
        start_input = input("What is the start time? [HH:MM:SS] ")
        startsecs = self.toSeconds(start_input) if start_input.strip() else None

        end_input = input("What is the end time? [HH:MM:SS] ")
        endsecs = self.toSeconds(end_input) if end_input.strip() else None

        if not self.validate_segment(segment, startsecs, endsecs):
            return

        season = None
        episode = None
        mapping = None

        if mediaObject.type == "tv":
            try:
                season = int(input("What season? "))
                episode = int(input("What episode? "))
            except ValueError:
                print("Season and episode must be integers.")
                return

            mapping_input = input("What episode mapping order? [default (default), official, dvd, alternate, absolute, regional] ") or "default"
            mapping = None if mapping_input.strip().lower() == "default" else mapping_input.strip()

        self.submit_timestamp(
            media_id=mediaObject.TMDBid,
            media_type=mediaObject.type,
            segment=segment,
            start_sec=startsecs,
            end_sec=endsecs,
            season=season,
            episode=episode,
            mapping=mapping
        )

    def submit_timestamp(
        self,
        media_id: int,
        media_type: str,
        segment: str,
        start_sec: Optional[float],
        end_sec: Optional[float],
        season: Optional[int] = None,
        episode: Optional[int] = None,
        mapping: Optional[str] = None
    ) -> None:
        if not self.INTRO_APIKEY:
            self.INTRO_APIKEY = prompt_for_key("INTRO_APIKEY", "TheIntroDB API Key")

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.INTRO_APIKEY}"
        }

        data = {
            "tmdb_id": media_id,
            "type": media_type,
            "segment": segment,
            "start_sec": start_sec,
            "end_sec": end_sec,
        }

        if media_type == "tv":
            data["season"] = season
            data["episode"] = episode
            if mapping:
                data["mapping"] = mapping

        response = requests.post(self.INTRO_submit, headers=headers, json=data)
        if response.status_code in (401, 403):
            print(f"\nAuthentication failed with TheIntroDB ({response.status_code}).")
            self.INTRO_APIKEY = prompt_for_key("INTRO_APIKEY", "new TheIntroDB API Key")
            headers["Authorization"] = f"Bearer {self.INTRO_APIKEY}"
            response = requests.post(self.INTRO_submit, headers=headers, json=data)

        print("\nresponse")
        self.checkSubmission(response)

    def constructTIDBPostTV(self, id: int, type: str, season: int, episode: int, segment: str, start: Optional[float], end: Optional[float], mapping: Optional[str] = None) -> None:
        """Backwards compatibility alias for TV submissions."""
        self.submit_timestamp(id, type, segment, start, end, season=season, episode=episode, mapping=mapping)

    def constructTIDBPostFilm(self, id: int, type: str, segment: str, start: Optional[float], end: Optional[float]) -> None:
        """Backwards compatibility alias for movie submissions."""
        self.submit_timestamp(id, type, segment, start, end)

    def checkSubmission(self, response: requests.Response) -> None:
        if response.status_code == 200 and response.json().get('ok') is True:
            submission_json = response.json()
            print("Submitted successfully")
            for sub in submission_json.get('submissions', []):
                print(f"id: {sub.get('id')}")
                print(f"weight: {sub.get('weight')}")
                if sub.get('tvdbId') is not None:
                    print(f"tvdbId: {sub.get('tvdbId')}")
        else:
            print(f"Submission failed with code {response.status_code}")
            print(response.text)


def main():
    introsubmitter = introSubmitter()
    choice = input("Search for a film or show? ") or "show"
    title_query = input("Title? ").strip()
    if not title_query:
        print("Title cannot be empty.")
        return

    if choice.strip().lower() == "film":
        introsubmitter.showInfo(introsubmitter.searchForFilm(title_query))
    else:
        introsubmitter.showInfo(introsubmitter.searchForTV(title_query))


if __name__ == "__main__":
    main()

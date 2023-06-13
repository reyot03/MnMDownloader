import asyncio
import os
from bs4 import BeautifulSoup as bs
# import requests
from urllib import request
from requests_html import AsyncHTMLSession
import time
import re
import mangagodownloader

# from urllib.parse import urlparse
# from utils.ImagesGetter import get_imgurls, main_get_images
# from utils.ImgToPdf import pdf_maker


class Manga_Site:
    def __init__(self) -> None:
        self.HEADERS = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
        self.manga_selected = None
        self.manga_name = None



class Mangago(Manga_Site):
    def __init__(self) -> None:
        super().__init__()
        import utils.mangagoKey
        (self.key, self.iv) = utils.mangagoKey.get_key_iv()
        self.key = bytes.fromhex(self.key)
        self.iv = bytes.fromhex(self.iv)

        self.site_name = "mangago.me"
        self.base_manga_search_url = "https://www.mangago.me/r/l_search/?name={}"
        self.manga_container_class = "pic_list"
        self.manga_container_id = "search_list"  # faster
        self.chapter_container_class = "listing"
        self.chapter_container_id = "chapter_table"
        self.manga_list = []
        self.chapter_list = []

    def filter_input(self):
        self.manga_search_input = self.manga_search_input.replace(' ', '+')
        self.manga_search_input = re.sub(r'[^+\-\w]+', '', self.manga_search_input)

    def search_manga(self, search_input):
        self.manga_search_input = search_input
        self.filter_input()
        print(
            '\n', f'Searching for {self.manga_search_input} in {self.site_name}'.upper(), '\n')
        self.get_manga_list()

    def request_page(self, url):
        connection_error_count = 0
        while True:
            try:
                req = request.Request(url, headers=self.HEADERS)
                resp = request.urlopen(req)
                return resp.read()
                break
            except:
                connection_error_count += 1
                print(f"Connection Error Occured {connection_error_count} times")
                time.sleep(1)

    def get_manga_list(self):
        search_url = self.base_manga_search_url.format(self.manga_search_input)
        # print(search_url)
        html_text = self.request_page(search_url)

        soup = bs(html_text, "html.parser")
        m_container = soup.find(id=self.manga_container_id).find_all('li')
        try:
            for m in m_container:
                manga = {}
                # manga["name"] = m.find(class_="tit").get_text(strip=True)
                manga["name"] = m.a["title"]
                manga["url"] = m.a["href"]
                try:
                    l = m.find(class_="chico")
                    if l:
                        manga["latest_chapter"] = l.get_text(strip=True)
                    else:
                        continue
                except:
                    continue
                self.manga_list.append(manga)

        except TypeError:
            print("Manga not found. Change the keyword")
            exit()
        except:
            print("Something went wrong while getting manga link")
            exit()
        # print(self.manga_list)

    def search_chapters(self, manga_selected):
        self.manga_selected = manga_selected
        self.manga_name = self.manga_list[self.manga_selected]["name"]
        print(
            '\n', f'Searching for {self.manga_name} in {self.site_name}'.upper(), '\n')
        self.get_chapter_list()

    def get_chapter_list(self):
        search_url = self.manga_list[self.manga_selected]["url"]
        html_text = self.request_page(search_url)

        soup = bs(html_text, "html.parser")
        ch_container = soup.find(id=self.chapter_container_id).find_all("tr")
        try:
            index = 1
            for ch in ch_container:
                chapter = {}
                chapter["name"] = re.sub(r'[^\w& ]+', '_', ch.a.get_text(strip=True))
                chapter["url"] = ch.a["href"]
                self.chapter_list.insert(0, chapter)
                index += 1
        except TypeError:
            print("No Chapters Found")
            exit()
        except:
            print("Something went wrong while getting chapters")
            exit()
        # print(self.chapter_list)

    def download_chapters(self, st_index, end_index):
        manga_path = f"./Downloads/{self.manga_name}"
        if not os.path.exists(manga_path):
            os.makedirs(manga_path)

        asession = AsyncHTMLSession()
        tasks = [lambda chapter=chapter:mangagodownloader.download_ch(asession, chapter["name"], chapter["url"], manga_path, self.key, self.iv) for chapter in self.chapter_list[st_index:(end_index+1)]]
        st_time = time.perf_counter()
        asession.run(*tasks)
        time_taken = time.perf_counter() - st_time
        print("\nDownload time:", time_taken)


class Mangakakalot(Manga_Site):
    # Error!!!: Image view/download from outside the site not allowed
    def __init__(self) -> None:
        super().__init__()
        self.site_name = "mangakakalot"
        self.base_manga_search_url = "https://mangakakalot.com/search/story/{}"
        self.manga_container_class = "story_item"
        self.chapter_container_class = ".row-content-chapter .a-h"
        self.manga_list = []
        self.chapter_list = []

    def filter_input(self):
        self.manga_search_input = self.manga_search_input.replace(' ', '_')
        self.manga_search_input = re.sub(r'\W+', '', self.manga_search_input)

    def search_manga(self, search_input):
        self.manga_search_input = search_input
        self.filter_input()
        print(
            '\n', f'Searching for {self.manga_search_input} in {self.site_name}'.upper(), '\n')
        self.get_manga_list()

    def request_page(self, url):
        with requests.Session() as session:
            connection_error_count = 0
            while True:
                try:
                    res = session.get(url, headers=self.HEADERS, timeout=10)
                    break
                except:
                    connection_error_count += 1
                    print(
                        f"Connection Error Occured {connection_error_count} time(s)")
                    time.delay(1)
                    pass
        return res

    def get_manga_list(self):
        search_url = self.base_manga_search_url.format(self.manga_search_input)
        res = self.request_page(search_url)

        soup = bs(res.text, "html.parser")
        URL_container = soup.find_all(class_=self.manga_container_class)
        # URL_container.find_all('a', href=True)
        try:
            index = 1
            for i in URL_container:
                manga = {}
                manga["name"] = i.find(
                    class_="story_name").get_text(strip=True)
                manga["url"] = i.a["href"]
                manga["latest_chapter"] = i.find(
                    class_="story_chapter").get_text(strip=True)
                self.manga_list.append(manga)
                index += 1

            # print(self.manga_list)
        except TypeError:
            print("Manga not found. Change the keyword")
            exit()
        except:
            print("Something went wrong while getting manga link")
            exit()

    def search_chapters(self, manga_selected):
        self.manga_selected = manga_selected
        self.manga_name = self.manga_list[self.manga_selected]["name"]
        print(
            '\n', f'Searching for {self.manga_name} in {self.site_name}'.upper(), '\n')
        self.get_chapter_list()

    def get_chapter_list(self):
        search_url = self.manga_list[self.manga_selected]["url"]
        res = self.request_page(search_url)

        soup = bs(res.text, "html.parser")
        URL_container = soup.select(self.chapter_container_class)
        # URL_container.find_all('a', href=True)
        try:
            index = 1
            for li in URL_container:
                chapter = {}
                chapter['name'] = li.a.get_text(strip=True)
                chapter["url"] = li.a["href"]
                self.chapter_list.insert(0, chapter)
                index += 1
        except TypeError:
            print("Chapters not found")
            exit()
        except:
            print("Something went wrong while getting chapters")
            exit()

    def download_chapters(self, st_index, end_index):
        if not os.path.exists(self.manga_name):
            os.mkdir(self.manga_name)

        for chapter in self.chapter_list[st_index:(end_index+1)]:
            chapter_name = self.chapter_list[chapter]["name"]
            chapter_url = self.chapter_list[chapter]["url"]
            print(f'Downloading {chapter_name}')
            # asyncio.run(main_get_images(chapter_name, chapter_url))
        print("Download Complete")


class Mangageko(Manga_Site):
    @classmethod
    def search_manga(cls, search_input):
        cls.manga_search_input = search_input
        print(f'Searching {cls.manga_search_input} in Mangageko')

    @classmethod
    def get_search_input(cls):
        return cls.manga_search_input


class Webtoons(Manga_Site):
    @classmethod
    def search_manga(cls, search_input):
        cls.manga_search_input = search_input
        print(f'Searching {cls.manga_search_input} in Webtoons')

    @classmethod
    def get_search_input(cls):
        return cls.manga_search_input


class Manga18fx(Manga_Site):
    @classmethod
    def search_manga(cls, search_input):
        cls.manga_search_input = search_input
        print(f'Searching {cls.manga_search_input} in Manga18fx')

    @classmethod
    def get_search_input(cls):
        return cls.manga_search_input
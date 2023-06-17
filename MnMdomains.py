from io import BytesIO
from PIL import Image, ImageOps
import re
from requests_html import AsyncHTMLSession
from urllib import request, parse, error
from bs4 import BeautifulSoup as bs
import os
import time
import mangagodownloader


class Manga_Site:
    def __init__(self) -> None:
        self.HEADERS = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
        self.manga_selected = None
        self.manga_name = None

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
            except:
                connection_error_count += 1
                if connection_error_count > 10:
                    exit()
                print(f"Connection Error Occured {connection_error_count} times")
                time.sleep(1)

    def get_manga_list(self):
        search_url = self.base_manga_search_url.format(self.manga_search_input)
        html_text = self.request_page(search_url)

        soup = bs(html_text, "html.parser")
        m_container = soup.find(class_=self.manga_container_class).find_all('li')
        try:
            for m in m_container:
                manga = {}
                manga["name"] = m.a["title"]
                manga["url"] = m.a["href"]
                if parse.urlparse(manga["url"]).netloc == '':
                    manga["url"] = parse.urljoin(self.base_url, manga["url"])
                try:
                    l = m.find(class_=self.latest_ch_class)
                    if l:
                        manga["latest_chapter"] = next(l.stripped_strings)
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

    def search_chapters(self, manga_selected):
        self.manga_selected = manga_selected
        self.manga_name = self.manga_list[self.manga_selected]["name"]
        print('\n', f'Searching for {self.manga_name} in {self.site_name}'.upper(), '\n')
        self.get_chapter_list()

    def get_chapter_list(self):
        search_url = self.manga_list[self.manga_selected]["url"]
        if self.site_name == "mangageko":
            search_url += "all-chapters"
        html_text = self.request_page(search_url)

        soup = bs(html_text, "html.parser")
        ch_container = soup.find(
            class_=self.chapter_container_class).find_all(self.chapter_tag)
        try:
            index = 1
            for ch in ch_container:
                chapter = {}
                chapter["name"] = re.sub(r'[^\w& ]+', '_', next(ch.a.stripped_strings))
                chapter["url"] = ch.a["href"]
                if parse.urlparse(chapter["url"]).netloc == '':
                    chapter["url"] = parse.urljoin(self.base_url, chapter["url"])
                self.chapter_list.insert(0, chapter)
                index += 1
        except TypeError:
            print("No Chapters Found")
            exit()
        except:
            print("Something went wrong while getting chapters")
            exit()


class Mangago(Manga_Site):
    def __init__(self) -> None:
        super().__init__()
        import utils.mangagoKey
        (self.key, self.iv) = utils.mangagoKey.get_key_iv()
        self.key = bytes.fromhex(self.key)
        self.iv = bytes.fromhex(self.iv)

        self.site_name = "mangago.me"
        self.base_url = "https://www.mangago.me"
        self.base_manga_search_url = "https://www.mangago.me/r/l_search/?name={}"
        self.manga_container_class = "pic_list"
        # self.manga_container_id = "search_list"  # faster but id not available for other classes
        self.latest_ch_class = "chico"
        self.chapter_container_class = "listing"
        self.chapter_container_id = "chapter_table"
        self.chapter_tag = 'tr'
        self.manga_list = []
        self.chapter_list = []

    def download_chapters(self, st_index, end_index):
        manga_path = f"./Downloads/{self.manga_name}"
        if not os.path.exists(manga_path):
            os.makedirs(manga_path)

        asession = AsyncHTMLSession()
        tasks = [lambda chapter=chapter:mangagodownloader.download_ch(
            asession, chapter["name"], chapter["url"], manga_path, self.key, self.iv) for chapter in self.chapter_list[st_index:(end_index+1)]]
        try:
            st_time = time.perf_counter()
            asession.run(*tasks)
            time_taken = time.perf_counter() - st_time
        except error.URLError:
            print("Couldn't connect to server")
            exit()
        print(f'\nDownload time: {time_taken:.2f}s')


class Mangageko(Manga_Site):
    def __init__(self) -> None:
        super().__init__()
        self.site_name = "mangageko"
        self.base_url = "https://www.mangageko.com"
        self.base_manga_search_url = "https://www.mangageko.com/search/?search={}"
        self.manga_container_class = "novel-list"
        self.latest_ch_class = "novel-stats"
        self.chapter_container_class = "chapter-list"
        self.chapter_tag = 'li'
        self.manga_list = []
        self.chapter_list = []

    @staticmethod
    async def get_urls(asession, chapter_url):
        res = await asession.get(chapter_url)
        imgs = res.html.find("#chapter-reader > img")
        img_urls = [img.attrs['src'] for img in imgs]
        return img_urls

    @staticmethod
    async def download_image(asession, img_url):
        res = await asession.get(img_url)
        image_content = Image.open(BytesIO(res.html.raw_html))
        if not (650 < image_content.size[0] < 850):
            image_content = ImageOps.contain(image_content, (728, 1024))
        return image_content

    @staticmethod
    async def img_to_pdf(pdf_path, images):
        images[0].save(pdf_path, "PDF", resolution=100.0,
                       save_all=True, append_images=images[1:])

    async def download_ch(self, asession, chapter_name, chapter_url, manga_path):
        print('Downloading', chapter_name)
        img_urls = await self.get_urls(asession, chapter_url)
        images = []
        for img_url in img_urls:
            images.append(await self.download_image(asession, img_url))

        # creating pdf
        pdf_path = f'{manga_path}/{chapter_name}.pdf'
        await self.img_to_pdf(pdf_path, images)

        print(f'\n{chapter_name} downloaded.')

    def download_chapters(self, st_index, end_index):
        manga_path = f"./Downloads/{self.manga_name}"
        if not os.path.exists(manga_path):
            os.makedirs(manga_path)

        asession = AsyncHTMLSession()
        tasks = [lambda chapter=chapter:self.download_ch(
            asession, chapter["name"], chapter["url"], manga_path) for chapter in self.chapter_list[st_index:(end_index+1)]]
        try:
            st_time = time.perf_counter()
            asession.run(*tasks)
            time_taken = time.perf_counter() - st_time
        except error.URLError:
            print("Couldn't connect to server")
            exit()
        print(f'\nDownload time: {time_taken:.2f}s')


class Webtoons(Manga_Site):
    @classmethod
    def search_manga(cls, search_input):
        cls.manga_search_input = search_input
        print(f'Searching {cls.manga_search_input} in Webtoons')

    @classmethod
    def get_search_input(cls):
        return cls.manga_search_input

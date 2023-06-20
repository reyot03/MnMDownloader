from io import BytesIO
from PIL import Image, ImageOps
import re
from requests_html import AsyncHTMLSession
from urllib import request, parse, error
from bs4 import BeautifulSoup as bs
from pathlib import Path
import time
from reportlab.pdfgen import canvas, pdfimages
from reportlab.lib.utils import ImageReader
from Crypto.Cipher import AES
import base64
import constants
import math
import gc


class Manga_Site:
    def __init__(self) -> None:
        self.HEADERS = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
        self.manga_selected = None
        self.manga_name = None

    def filter_input(self):
        self.manga_search_input = self.manga_search_input.replace(' ', '+')
        self.manga_search_input = re.sub(
            r'[^+\-\w]+', '', self.manga_search_input)

    def search_manga(self, search_input):
        self.manga_search_input = search_input
        self.filter_input()
        print(
            '\n', f'Searching for {self.manga_search_input.replace("+", " ")} in {self.site_name}'.upper(), '\n')
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
                print(
                    f"Connection Error Occured {connection_error_count} times")
                time.sleep(1)

    def get_manga_list(self):
        search_url = self.base_manga_search_url.format(self.manga_search_input)
        html_text = self.request_page(search_url)

        soup = bs(html_text, "html.parser")
        m_container = soup.find(
            class_=self.manga_container_class).find_all('li')
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
        print(
            '\n', f'Searching for {self.manga_name} in {self.site_name}'.upper(), '\n')
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
                chapter["name"] = re.sub(
                    r'[^\w& ]+', '_', next(ch.a.stripped_strings))
                chapter["url"] = ch.a["href"]
                if parse.urlparse(chapter["url"]).netloc == '':
                    chapter["url"] = parse.urljoin(
                        self.base_url, chapter["url"])
                self.chapter_list.insert(0, chapter)
                index += 1
        except TypeError:
            print("No Chapters Found")
            exit()
        except:
            print("Something went wrong while getting chapters")
            exit()

    @staticmethod
    async def get_urls(asession, chapter_url):
        res = await asession.get(chapter_url)
        imgs = res.html.find("#chapter-reader > img")
        img_urls = [img.attrs['src'] for img in imgs]
        return img_urls

    @staticmethod
    async def download_image(asession, img_url):
        res = await asession.get(img_url)
        image_content = Image.open(BytesIO(res.content))
        return image_content

    @staticmethod
    async def img_to_pdf_low(pdf_path, images):
        first_page = True
        # making width of pages close to width of first page
        for pos, image in enumerate(images):
            if first_page:
                page_width, page_height = image.size
                first_page = False
            if not ((page_width-150) < image.size[0] < (page_width+150)):
                new_image = ImageOps.contain(image, (page_width, page_height))
                images[pos] = new_image
        images[0].save(pdf_path, "PDF", save_all=True,
                       append_images=images[1:])

    @staticmethod
    async def img_to_pdf_high(pdf_path, images):
        c = canvas.Canvas(pdf_path)
        first_page = True
        for im in images:
            im_width, im_height = im.size
            if first_page:
                first_page_width = im_width
                first_page = False
            if not ((first_page_width-150) < im_width < (first_page_width+150)):
                width_ratio = first_page_width / im_width
                im_width = first_page_width
                im_height = int(width_ratio * im_height)
            c.setPageSize((im_width, im_height))
            # PIL.Image -> BytesIO -> ImageReader to decrease pdf size
            with BytesIO() as buffer:
                im.save(buffer, format=im.format)
                buffer.seek(0)
                c.drawImage(ImageReader(buffer), 0, 0, im_width, im_height)
            c.showPage()
        c.save()
        # del c
        # del images
        # gc.collect()

    async def download_ch(self, asession, chapter_name, chapter_url, manga_path):
        print('Downloading', chapter_name)
        img_urls = await self.get_urls(asession, chapter_url)
        images = []
        for img_url in img_urls:
            images.append(await self.download_image(asession, img_url))

        # creating pdf
        pdf_path = f'{manga_path}/{chapter_name}.pdf'
        await self.img_to_pdf_high(pdf_path, images)

        print(f'\n{chapter_name} downloaded.')

    def download_chapters(self, st_index, end_index):
        manga_path = Path('Downloads', self.manga_name)
        manga_path.mkdir(parents=True, exist_ok=True)

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

    @staticmethod
    async def unscramble_image(url, res):
        IMGKEYS = constants.IMGKEYS
        MK1 = constants.MK1
        MK2 = constants.MK2
        MK1_VAL = constants.MK1_VAL
        MK2_VAL = constants.MK2_VAL

        unscrambled = False
        im = BytesIO(res.content)

        for m in ([*IMGKEYS] + [MK1] + [MK2]):
            if m in url:
                st_time = time.perf_counter()
                unscrambled = True
                im = Image.open(im)
                width, height = im.size
                img_ext = im.format
                im_new = Image.new(im.mode, im.size)

                unscramble_key = IMGKEYS[m]

                if MK1 in url or MK2 in url:
                    _0X2c9a16 = MK1_VAL if MK1 in url else MK2_VAL
                    estr = _0X2c9a16
                    ekey = estr[19]
                    ekey = ekey + estr[23]
                    ekey = ekey + estr[31]
                    ekey = ekey + estr[39]

                    estr = _0X2c9a16[0:19]
                    estr += _0X2c9a16[20:23]
                    estr += _0X2c9a16[24:31]
                    estr += _0X2c9a16[32:39]
                    estr += _0X2c9a16[40:]
                    estr_len = len(estr)

                    for j in [3, 2]:
                        for i in range(estr_len-1, int(ekey[j])-1, -1):
                            # swap characters at pos and i
                            pos = i - int(ekey[j])
                            estr = estr[:pos] + estr[i] + \
                                estr[pos+1:i] + estr[pos] + estr[i+1:]

                    for j in [1, 0]:
                        for i in range(estr_len-1, int(ekey[j])-1, -1):
                            if i & 1:       # check if odd
                                estr = estr[:pos] + estr[i] + \
                                    estr[pos+1:i] + estr[pos] + estr[i+1:]

                    unscramble_key = estr

                unscramble_key = unscramble_key.split('a')
                widthnum = height_num = 9
                sm_width = width / widthnum
                sm_height = height / height_num

                for i in range(0, (widthnum * height_num)):
                    k = 0 if not unscramble_key[i].isdigit(
                    ) else float(unscramble_key[i])
                    _y = math.floor(k / height_num)
                    dst_y = _y * sm_height
                    dst_x = (k - _y * widthnum) * sm_width
                    _y = math.floor(i / widthnum)
                    src_y = _y * sm_height
                    src_x = (i - _y * widthnum) * sm_width
                    im_crop = im.crop((int(src_x), int(src_y), int(
                        src_x + sm_width), int(src_y + sm_height)))
                    im_new.paste(im_crop, box=(int(dst_x), int(dst_y)))

                fln = time.perf_counter() - st_time
                print(f"took {fln:.5f} to unscramble image")

        if unscrambled is False:
            print("without")
            return ImageReader(im)
        else:
            with BytesIO() as buffer:
                print("with scramble")
                im_new.save(buffer, format=img_ext)
                buffer.seek(0)
                return ImageReader(im_new)

    async def download_image(self, asession, img_url):
        res = await asession.get(img_url)
        image_content = await self.unscramble_image(img_url, res)
        return image_content

    async def get_urls(self, asession, chapter_url):
        res = await asession.get(chapter_url)
        script = res.html.find('script', containing='imgsrcs', first=True)
        imgsrcs = script.search('imgsrcs = {};')[0][1:-1]
        imgsrcs = base64.b64decode(imgsrcs)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        img_urls = cipher.decrypt(imgsrcs).strip(b'\x00').decode('utf-8')
        img_urls = img_urls.split(',')
        return img_urls


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


class Webtoons(Manga_Site):
    @classmethod
    def search_manga(cls, search_input):
        cls.manga_search_input = search_input
        print(f'Searching {cls.manga_search_input} in Webtoons')

    @classmethod
    def get_search_input(cls):
        return cls.manga_search_input

from io import BytesIO
from PIL import Image
import re
from requests_html import AsyncHTMLSession, HTMLSession
from urllib import parse
from bs4 import BeautifulSoup as bs
from pathlib import Path
import time
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from Crypto.Cipher import AES
import base64
import constants
import math


class Manga_Site:
    def __init__(self):
        self.manga_selected = None
        self.manga_name = None
        self.pdf_request = None
        self.img_request = None
        self.manga_list = []
        self.chapter_list = []
        self.session = HTMLSession()

    def filter_input(self):
        self.manga_search_input = self.manga_search_input.replace(' ', '+')
        self.manga_search_input = re.sub(r'[^+\-\w]+', '', self.manga_search_input)

    def request_page(self, url):
        try:
            res = self.session.get(url)
            self.base_url = res.html.base_url
            return res.content
        except:
            print("Couldn't connect to server")
            exit()

    def search_manga(self, search_input):
        self.manga_search_input = search_input
        self.filter_input()
        print(f'\nSearching for {self.manga_search_input.replace("+", " ")} in {self.site_name}')
        search_url = self.base_manga_search_url.format(self.manga_search_input)
        html_content = self.request_page(search_url)
        # scrap manga names, chapter-urls, and latest chapter name
        soup = bs(html_content, "html.parser")
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
        except:
            print("Site changed")

    def search_chapters(self, manga_selected):
        self.manga_selected = manga_selected
        self.manga_name = self.manga_list[self.manga_selected]["name"]
        print(f'Searching for chapters of {self.manga_name} in {self.site_name}')
        # select manga url from manga-list using manga_selected integer
        search_url = self.manga_list[self.manga_selected]["url"]
        if self.site_name == "mangageko":
            search_url = parse.urljoin(search_url, "/all-chapters")
        html_content = self.request_page(search_url)
        # scrap chapter names and urls from that manga url
        soup = bs(html_content, "html.parser")
        ch_container = soup.find(class_=self.chapter_container_class).find_all(self.chapter_tag)
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
            print("Site changed")

    async def get_urls(self, chapter_url):
        res = await self.session.get(chapter_url)
        imgs = res.html.find("#chapter-reader > img")
        img_urls = [img.attrs['src'] for img in imgs]
        return img_urls

    async def download_image(self, img_url):
        res = await self.session.get(img_url)
        image_content = Image.open(BytesIO(res.content))
        return image_content

    @staticmethod
    async def save_pdf(pdf_path, images):
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
            # BytesIO -> PIL.Image -> BytesIO -> ImageReader decreases pdf size
            with BytesIO() as buffer:
                im.save(buffer, format=im.format)
                buffer.seek(0)
                c.drawImage(ImageReader(buffer), 0, 0, im_width, im_height)
            c.showPage()
        c.save()

    @staticmethod
    async def save_images(ch_path, images):
        for pg, im in enumerate(images):
            im.save(Path(ch_path, f'{pg+1}.{im.format}'))

    async def download_ch(self, chapter_name, chapter_url, manga_path):
        print('Downloading', chapter_name)
        img_urls = await self.get_urls(chapter_url)
        images = []
        for img_url in img_urls:
            images.append(await self.download_image(img_url))
        # creating pdf and images
        ch_path = Path(manga_path, chapter_name)
        pdf_path = f'{ch_path}.pdf'
        if self.img_request:
            ch_path.mkdir(parents=True, exist_ok=True)
            await self.save_images(ch_path, images)
        if self.pdf_request:
            await self.save_pdf(pdf_path, images)
        print(f'\n{chapter_name} downloaded.')

    def download_chapters(self, st_index, end_index):
        manga_path = Path('Downloads', self.manga_name)
        manga_path.mkdir(parents=True, exist_ok=True)
        # using requests-html asynchronous session
        self.session.close()
        self.session = AsyncHTMLSession()
        tasks = [lambda chapter=chapter:self.download_ch(
            chapter["name"], chapter["url"], manga_path) for chapter in self.chapter_list[st_index:(end_index+1)]]
        st_time = time.perf_counter()
        self.session.run(*tasks)
        time_taken = time.perf_counter() - st_time
        print(f'\nDownload time: {time_taken:.2f}s')


class Mangago(Manga_Site):
    def __init__(self):
        super().__init__()
        import utils.mangagoKey
        self.key, self.iv = utils.mangagoKey.get_key_iv(self.session)
        # site information to scrap data
        self.site_name = "mangago.me"
        self.base_url = "https://www.mangago.me"
        self.base_manga_search_url = "https://www.mangago.me/r/l_search/?name={}"
        self.manga_container_class = "pic_list"
        # self.manga_container_id = "search_list"  # faster but id not available for other Sites
        self.latest_ch_class = "chico"
        self.chapter_container_class = "listing"
        self.chapter_container_id = "chapter_table"
        self.chapter_tag = 'tr'

    @staticmethod
    def unscramble_image(url, res):
        IMGKEYS = constants.IMGKEYS
        MK1 = constants.MK1
        MK2 = constants.MK2
        MK1_VAL = constants.MK1_VAL
        MK2_VAL = constants.MK2_VAL
        # unscramble images if url is match else return same image as PIL.Image object
        unscrambled = False
        im = Image.open(BytesIO(res.content))
        for m in ([*IMGKEYS] + [MK1] + [MK2]):
            if m in url:
                st_time = time.perf_counter()
                unscrambled = True
                width, height = im.size
                im_new = Image.new(im.mode, im.size)
                if (MK1 in url) or (MK2 in url):
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
                    for j in range(3, -1, -1):
                        for i in range(estr_len-1, int(ekey[j])-1, -1):
                            if i & 1:       # check if odd
                                # swap characters at pos and i
                                pos = i - int(ekey[j])
                                estr = estr[:pos] + estr[i] + estr[pos+1:i] + estr[pos] + estr[i+1:]
                    unscramble_key = estr
                else:
                    unscramble_key = IMGKEYS[m]
                # unscrambling image here
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
                    im_crop = im.crop((int(src_x), int(src_y), int(src_x + sm_width), int(src_y + sm_height)))
                    im_new.paste(im_crop, box=(int(dst_x), int(dst_y)))
                fln = time.perf_counter() - st_time
                im_new.format = im.format
                print(f"took {fln:.5f} to unscramble image")
        if unscrambled is False:
            return im
        return im_new

    async def download_image(self, img_url):
        res = await self.session.get(img_url)
        image_content = self.unscramble_image(img_url, res)
        return image_content

    async def get_urls(self, chapter_url):
        res = await self.session.get(chapter_url)
        script = res.html.find('script', containing='imgsrcs', first=True)
        imgsrcs = script.search('imgsrcs = {};')[0][1:-1]
        imgsrcs = base64.b64decode(imgsrcs)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        img_urls = cipher.decrypt(imgsrcs).strip(b'\x00').decode('utf-8')
        img_urls = img_urls.split(',')
        return img_urls


class Mangageko(Manga_Site):
    def __init__(self):
        super().__init__()
        # site information to scrap data
        # Mangageko is subclass of Manga_Site, so inherits all methods from there
        self.site_name = "mangageko"
        self.base_url = "https://www.mangageko.com"
        self.base_manga_search_url = "https://www.mangageko.com/search/?search={}"
        self.manga_container_class = "novel-list"
        self.latest_ch_class = "novel-stats"
        self.chapter_container_class = "chapter-list"
        self.chapter_tag = 'li'

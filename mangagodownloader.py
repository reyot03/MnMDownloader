from Crypto.Cipher import AES
import base64
import aiofiles
import os
import imgkeys
from io import BytesIO
from PIL import Image
import math
import time

async def unscramble_image(url, res):
    _imgkeys_ = imgkeys._imgkeys_
    mk1 = imgkeys.mk1
    mk2 = imgkeys.mk2
    mk1_val = imgkeys.mk1_val
    mk2_val = imgkeys.mk2_val

    unscrambled = False
    for m in ([*_imgkeys_] + [mk1] + [mk2]):
        if m in url:
            st_time = time.perf_counter()
            unscrambled = True
            buffer = BytesIO()
            im = Image.open(BytesIO(res.html.raw_html))
            width, height = im.size
            img_ext = im.format
            im_new = Image.new(im.mode, im.size)

            unscramble_key = _imgkeys_[m]

            if mk1 in url or mk2 in url:
                _0X2c9a16 = mk1_val if mk1 in url else mk2_val
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
                        estr = estr[:pos] + estr[i] + estr[pos+1:i] + estr[pos] + estr[i+1:] 

                for j in [1, 0]:
                    for i in range(estr_len-1, int(ekey[j])-1, -1):
                        if i & 1:       # check if odd
                            estr = estr[:pos] + estr[i] + estr[pos+1:i] + estr[pos] + estr[i+1:] 

                unscramble_key = estr

            unscramble_key = unscramble_key.split('a')
            widthnum = height_num = 9
            sm_width = width / widthnum
            sm_height = height / height_num

            for i in range(0, (widthnum * height_num)):
                k = 0 if not unscramble_key[i].isdigit() else float(unscramble_key[i])
                _y = math.floor(k / height_num)                                 # 
                dst_y = _y * sm_height
                dst_x = (k - _y * widthnum) * sm_width
                _y = math.floor(i / widthnum)
                src_y = _y * sm_height
                src_x = (i - _y * widthnum) * sm_width
                im_crop = im.crop((int(src_x), int(src_y), int(src_x + sm_width), int(src_y + sm_height)))
                im_new.paste(im_crop, box=(int(dst_x), int(dst_y)))

            im_new.save(buffer, format=img_ext)

            fln = time.perf_counter() - st_time
            print("took", fln, "to unscramble image")

    if unscrambled is False:
        return res.content
    else:
        return buffer.getbuffer()
            

async def download_image(asession, ch_path, img_url, page_num):
    res = await asession.get(img_url)
    image_content = await unscramble_image(img_url, res)
    ext = os.path.splitext(img_url)[1]
    img_path = '{}/Page{}{}'.format(ch_path, page_num, ext or '.jpeg')
    f = await aiofiles.open(img_path, mode="wb")
    await f.write(image_content)
    f.close()

async def get_urls(asession, chapter_url, key, iv):
    res = await asession.get(chapter_url)
    script = res.html.find('script', containing='imgsrcs', first=True)
    imgsrcs = script.search('imgsrcs = {};')[0][1:-1]
    imgsrcs = base64.b64decode(imgsrcs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    img_urls = cipher.decrypt(imgsrcs).strip(b'\x00').decode('utf-8')
    img_urls = img_urls.split(',')
    return img_urls

async def download_ch(asession, chapter_name, chapter_url, manga_path, key, iv):
    print('Downloading', chapter_name)
    img_urls = await get_urls(asession, chapter_url, key, iv)
    ch_path = f'{manga_path}/{chapter_name}'
    if not os.path.exists(ch_path):
        os.mkdir(ch_path)
    page_num = 0
    for img_url in img_urls:
        page_num += 1
        await download_image(asession, ch_path, img_url, page_num)
    print(f'\n{chapter_name} downloaded.')

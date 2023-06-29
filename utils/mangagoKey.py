import re


def decode_sojson_v4(jsf):
    head = "['sojson.v4']"
    if type(jsf) == bytes:
        jsf = jsf.decode()
    if head not in jsf:
        return False
    args = re.findall(r'\d+', jsf[240:-58])
    text = ''.join(map(lambda x: chr(int(x)), args))
    return text


def get_key_iv(session):
    chap_url = "https://www.mangago.me/read-manga/onepunch_man/mh/c001/"
    res = session.get(chap_url)
    # extract script_url containing sojson.v4 encoded key and iv
    scripts = res.html.find('script[src]')
    script_url = [s.attrs['src'] for s in scripts if 'chapter.js' in s.html][0]
    # decrypt sojson.v4 script and find key and iv
    encrypted_script = session.get(script_url).content
    if not encrypted_script:
        print("using custom key")
        return (b'\xe1\x1a\xdc9I\xbaY\xab\xbeV\xe0W\xf2\x0f\x88>', b'\x124Vx\x90\xab\xcd\xef\x124Vx\x90\xab\xcd\xef')
    decripted_script = decode_sojson_v4(encrypted_script)
    key = re.search(r'key\W+=\W+CryptoJS.enc.Hex.parse\(\W(.*?)\W\);', decripted_script).group(1)
    iv = re.search(r'iv\W+=\W+CryptoJS.enc.Hex.parse\(\W(.*?)\W\);', decripted_script).group(1)
    key = bytes.fromhex(key)
    iv = bytes.fromhex(iv)
    return (key, iv)

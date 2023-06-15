from urllib import request
from bs4 import BeautifulSoup as bs
import re


HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}

def get_page(chap_url):
	req = request.Request(chap_url, headers=HEADERS)
	resp = request.urlopen(req)
	html_text = resp.read()
	return html_text

def decode_sojson_v4(jsf):
    head = "['sojson.v4']"
    jsf = str(jsf)
    if head not in jsf:
        return False
    args = re.findall(r'\d+', jsf[240:-58])
    text = ''.join(map(lambda x: chr(int(x)), args))
    return text

def get_key_iv():
	chap_url = "https://www.mangago.me/read-manga/onepunch_man/mh/c001/"
	# get html page
	html_text = get_page(chap_url)

	# extract script_url containing sojson.v4 encoded key and iv
	soup = bs(html_text, 'html.parser')
	pattern = re.compile(r"https://.+/chapter\.js.+")
	script_url = soup.find("script", src=pattern)["src"]

	# decrypt sojson.v4 script and find key and iv
	encrypted_script = get_page(script_url).decode()
	decripted_script = decode_sojson_v4(encrypted_script)
	if not decripted_script:
		return ('e11adc3949ba59abbe56e057f20f883e', '1234567890abcdef1234567890abcdef')
	key = re.search(r'var key = CryptoJS.enc.Hex.parse\(\W(.*?)\W\);'.replace(' ', r'\W+'), decripted_script).group(1)
	iv = re.search(r'var iv = CryptoJS.enc.Hex.parse\(\W(.*?)\W\);'.replace(' ', r'\W+'), decripted_script).group(1)

	return (key, iv)

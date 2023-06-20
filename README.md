# MnMDownloader
Simple python program to scrap Manga, Manhua, Manhwa and Webtoon chapters.

Outputs are in PDF format.

## Installation

Clone the project

```bash
git clone https://github.com/reyot03/MnMDownloader
```

Install dependencies [[inside virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)]

```bash
pip install -r requirements.txt
```
## Usage/Examples

* MnMDownloader downloads only first one chapter by default.

        python mnmdownloader.py one-punch man

* Give [-i] and [-f] parameters to download multiple chapters.

        python mnmdownloader.py one-punch man -i 5 -f 8

* If only [-i] parameter is given, it downloads only that specific chapter.

        python mnmdownloader.py one-punch man -i 5

    and

        python mnmdownloader.py one-punch man -i 5 -f 5

    are same

* If only [-f] parameter is given, it downloads first [-f] chapters.

        python mnmdownloader.py one-punch man -f 8
    
    and

        python mnmdownloader.py one-punch man -i 1 -f 8

    are same

*  Use [--chlist] to check the list of available chapters

        py mnmdownloader.py one-punch man --chlist

* Use [--mlist] to check the list for search result with name [manga]

        py mnmdownloader.py one-punch man --mlist

* To download second manga from list of search result

        py mnmdownloader.py one-punch man -m 2
    
    downloads One-Punch Man [ONE]

* Use [--slist] to view site names and [-s] to use the site. Default is mangago

        py mnmdownloader.py --slist
        
        py mnmdownloader.py -s mangageko one-punch man -i 5

## Supported Sites
* [mangageko](https://www.mangageko.com/)
* [mangago](https://mangago.me/)

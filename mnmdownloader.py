import mnmdomains
import argparse


def show_list(li):
    index = 1
    for item in li:
        print(f"{index}. {item}")
        index += 1


def warn_invalid_select():
    print("\nValue for --m, -i & -f should be an integer within search result.\nUse --mlist & chlist to show manga list & chapter list respectively.\n")


def check_positive(string):
    value = float(string)
    if value != int(value) or value < 1:
        warn_invalid_select()
        raise argparse.ArgumentTypeError()
    return value


if __name__ == '__main__':
    SITES = {
        'mangago': mnmdomains.Mangago,
        'mangageko': mnmdomains.Mangageko
    }

    parser = argparse.ArgumentParser(description='''
                        MnMDownloader is for downloading manga by webscraping.
                            It downloads only first one chapter by default.
                     Give [-i] and [-f] parameters to download multiple chapters.
                If only [-i] parameter is given, it downloads only that specific chapter.
        Index and actual chapter of manga might be different so use [--chlist] to check the list

    Examples: 
    To download manga "one-punch man" from chapter 1 to chapter 5
    py main.py one-punch man -i 1 -f 5

    To see all available chapters
    py main.py one-punch man --chlist


    To see similar manga with key-word one-punch man
    py main.py one-punch man --mlist

    To download second manga in manga list from chapter 3 to 5
    py main.py one-punch man -m 2 -i 3 -f 5
    ''', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--slist', action='store_true', help='List the sites available to download manga from')
    parser.add_argument('manga_name', metavar='manga', nargs='*', help='Name of the manga to download',  type=str)
    parser.add_argument('-s', '--site', choices=SITES.keys(), default='mangago', help='Site of manga download')
    parser.add_argument('--mlist', action='store_true', help='List the manga available for input term')
    parser.add_argument('--chlist', action='store_true', help='List the chapter available for selected manga')
    parser.add_argument('-m', '--mselect', type=check_positive, default=1,
                        help='index of manga to download. use --mlist to see the list')
    parser.add_argument('-i', '--start', default=1, type=check_positive, help='Starting Chapter to download')
    parser.add_argument('-f', '--end', default=1, type=check_positive, help='Ending Chapter to download')

    args = parser.parse_args()

    if args.slist:
        show_list(SITES.keys())

    elif not args.manga_name:
        print("Give me a name of manga to download")

    elif args.start > args.end:
        print("Index of final chapter [-f] can't be greater than starting chapter [-i]\n")
        print(parser.parse_args(['-h']))

    else:
        manga = SITES[args.site]()
        manga_name = ' '.join(args.manga_name)
        manga.search_manga(manga_name)
        if not len(manga.manga_list):
            print("No manga found!! Try different keywords")

        elif args.mlist:
            show_list(f'{m["name"]} | Latest Chapter: {m["latest_chapter"]}' for m in manga.manga_list)

        elif args.mselect > len(manga.manga_list):
            warn_invalid_select()
        else:
            manga.search_chapters(args.mselect - 1)
            if args.chlist:
                print(f"Manga: {manga.manga_name} \nChapters:".upper())
                chapters = [chapter["name"] for chapter in manga.chapter_list]
                show_list(chapters)
            elif args.end > len(manga.chapter_list):
                warn_invalid_select()
            else:
                manga.download_chapters(args.start-1, args.end-1)

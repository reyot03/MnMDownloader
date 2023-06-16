import inspect, MnMdomains
from decor import *
chapter_selected = None


def show_list(li):
    index = 1
    for item in li:
        print(f"{index}. {item}")
        index += 1


def check_num(length, selected):
    try:
        if selected.isnumeric():
            if int(selected) in range(1, length+1):
                return True
    except ValueError:
        print("Some value error")
        exit()
    except:
        print('Something when wrong while selecting')
        exit()
    if selected == '':
        last_exit_check()
    else:
        print_hline()
        print(f'\nInvalid input {selected} was given\n')
    return False


def select_num(text, length):
    selected = input(text)
    if check_num(length, selected):
        return int(selected)
    else:
        return select_num(text, length)


def input_manga():
    manga_name = input("Please enter name of the manga: ")
    manga_name = ''.join(c for c in manga_name if c.isalnum() or c == ' ' or c == '-')
    if manga_name == '':
        last_exit_check()
    else:
        return manga_name
    print_hline()
    return input_manga()


def select_chapters(chapters):
    s = select_num("\nStarting Chapter to download: ", len(chapters))
    f = select_num("Ending Chapter to download: ", len(chapters))
    if s <= f:
        return s, f
    else:
        print("Starting Chapter can't be greater than End Chapter\n")
        return select_chapters(chapters)

def get_sites():
    SITE_NAMES = []
    SITE_CLASSES = []

    for name, cls in inspect.getmembers(MnMdomains, inspect.isclass):
        if name != 'Manga_Site' and cls.__module__ == 'MnMdomains':
            SITE_NAMES.append(name)
            SITE_CLASSES.append(cls)

    return (SITE_NAMES, SITE_CLASSES)


def main():
    SITE_NAMES, SITE_CLASSES = get_sites()
    # show list of sites and choose which site to download from
    show_list(SITE_NAMES)
    site_selected = select_num("Please select site to download from: ", len(SITE_NAMES))

    # show selected site and input the name of manga
    print(
        '\n', f"Selected Site is {SITE_NAMES[site_selected - 1]}".upper(), '\n')
    manga_search_input = input_manga()

    # create object corresponding to selected site
    manga_site = SITE_CLASSES[site_selected-1]
    manga = manga_site()

    while not len(manga.manga_list):
        # search for string from input in the site
        manga.search_manga(manga_search_input)
        if not len(manga.manga_list):
            print("No manga found!! Try different keywords")

    # show the list of manga search result and choose one
    # show_manga(manga.manga_list)
    show_list(
        f'{m["name"]} | Latest Chapter: {m["latest_chapter"]}' for m in manga.manga_list)
    manga_selected = select_num(
        "\nSelect the manga to download from above result: ", len(manga.manga_list)) - 1

    # search chapters of chosen manga
    manga.search_chapters(manga_selected)

    download_more = True
    while download_more:
        # show the list of chapters and choose start and end chapters
        print('\n', f"Manga: {manga.manga_name} \n Chapters:".upper())
        chapters = [chapter["name"] for chapter in manga.chapter_list]
        show_list(chapters)
        s, f = select_chapters(chapters)
        manga.download_chapters(s-1, f-1)
        check_download_more = input("Enter y/Y to download more: ")
        if not check_download_more in ['y', 'Y']:
            download_more = False


if __name__ == '__main__':
    main()

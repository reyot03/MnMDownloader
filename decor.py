def print_hline():
    print('-'*50)


def last_exit_check():
    check_exit = input('Press C to continue or Enter to exit: ')
    if check_exit == '':
        exit()
    if check_exit in ['c', 'C']:
        return
    last_exit_check()

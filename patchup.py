# coding:utf-8
import os
import click
import re
from subprocess import check_output


def log_w(value):
    click.secho("Warning   {}".format(value), fg='red')

def log(log_information, value):
    click.echo("{} {}-------------------->  {}".format(click.style("Log", fg="white", bg='green'), log_information, value))


def log_debug(*args):
    if len(args) == 1:
        click.echo("{} {}".format(click.style("DEBUG", fg="white", bg='blue'), args[0]))
    elif len(args) == 2:
        click.echo(
            "{} {}-------------------->  {}".format(click.style("DEBUG", fg="white", bg='blue'), args[0], args[1]))
    else:
        log_w("Use error:log_debug")
        exit()


def log_info(value):
    click.echo("{} {}".format(click.style("INFO", fg="yellow", bg='white'), value))


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def pretreatment_arch(program_name):
    """获取程序的位数"""
    program_path = os.path.abspath(program_name)
    recv = os.popen('file ' + program_path).read()  # 执行file命令，来对获取的数据进行处理，以来判断程序的位数
    if '64-bit' in recv:
        arch = '64'
        log('arch', 'amd64')
    elif '32-bit' in recv:
        arch = 'i386'
        log('arch', 'i386')
    else:
        log_w('It may not be an ELF file, its type is {}'.format(recv))
        exit()
    return arch


def download_libc(glibc_path, list, debug):
    """给出libc名称，去进行下载（只有在libs目录中没有搜到所需libc时，才会触发此函数）"""
    try:
        choice = raw_input("The libc library and linker you need are matched "
                           "in the glibc all in one list file. You can choose "
                           "to download them by selecting the corresponding "
                           "subscript index, or enter q to exit\n")
    except:
        choice = input("The libc library and linker you need are matched "
                           "in the glibc all in one list file. You can choose "
                           "to download them by selecting the corresponding "
                           "subscript index, or enter q to exit\n")
    if choice == 'q':
        log_info("Normal exit")
        exit()
    if choice.isdigit():
        choice = int(choice)
    else:
        log_w("Illegal selection")
        exit()
    if choice > (len(list) - 1):
        log_w("Illegal selection")
        exit()
    else:
        if debug:
            log_debug(glibc_path + '/download ' + "".join(list[choice]))
        log_info("Please wait a moment. It's downloading for you")
        judge = os.popen(glibc_path + '/download ' + "".join(list[choice])).read()
        division = judge.split("\n")
        for i in division:
            if 'Failed' in i:
                log_w("Installation failed")
                exit()
        log_info("Libc library downloaded successfully")
        return list[choice]


def match_linker(libc_path, arch, all_files, glibc_path, debug):
    """去寻找与libc匹配的ld，如果没有则会尝试在glibc-all-in-one中list文件中搜索"""
    success_match = []
    libc_path = os.path.abspath(libc_path)  # 获取用户所指定的libc绝对路径

    try:
        recv = os.popen('strings ' + libc_path + ' | grep ubuntu').read()
    except:
        log_w("Maybe you don't have the strings command")
        exit()

    if not recv:
        log_w("There is no version information matching libc")
        exit()
    """利用正则表达式来获取libc的具体版本，以来匹配对应的ld"""
    p1 = re.compile(r"[(](.*)[)]")
    c = re.findall(p1, recv)
    strr = "".join(c)
    list = strr.split(" ")
    try:
        libc_edition = list[2]
    except:
        log_w("The correct libc information was not obtained")
        exit()
    version = libc_edition[:4]
    log("libc_edition", libc_edition)

    for i in all_files:
        if libc_edition in i:
            if arch in i:
                success_match.append(i)
    if not success_match:
        """如果没有在glibc-all-in-one中libs找到，则去list目录中进行匹配"""
        boolean = match_libc(glibc_path, libc_edition, arch, success_match)

        if boolean:
            success_match.append(download_libc(glibc_path, boolean, debug))
        else:
            log_w("No match to the corresponding linker")
            exit()
    log('match_linker_success_match', success_match)
    glibc_path = os.path.abspath('glibc-all-in-one')
    libc_path = glibc_path + '/libs/' + success_match[0]
    ld_path = libc_path + '/ld-' + version + '.so'
    log('ld_patch', ld_path)
    return ld_path


def match_libc(glibc_path, libc_version, arch, success_match):
    """在list中进行搜索，如果搜索成功，可以进行下载"""
    recv = os.popen('cat ' + glibc_path + '/list').read()
    list = recv.split("\n")
    for info in list:
        if libc_version in info:
            if arch in info:
                success_match.append(info)
    if not success_match:
        log_w("No suitable libc version was found in glibc all in one")
        return False
    else:
        log('match_libc_success_match', success_match)
        return success_match


@click.command(name='patchup', short_help="Patchelf executable file using glibc-all-in-one.")
@click.argument('program_name', type=str)
@click.argument('libc_edition', type=str)
@click.option('--backups', '-b', 'backup', is_flag=True, help="Backup target file or not.")
@click.option('--debug', '-d', 'debug', is_flag=True,
              help="if open debug,you can see some key information in the patch process")
@click.option('--choice', '-c', 'choice', is_flag=True, help="Choose libc version independently")
def patchup(program_name, libc_edition, backup,debug,choice):
    """PROGRAM_NAME: ELF executable filename.\n
     LIBC_EDITION: If you want to patch the libc which is given by the topic ,
     then you should enter its full name or path,for example /home/hacker/Desktop/libc-2.23.so.
     If the topic does not provide a specific libc version, then you can input its version number,
     and it will find the corresponding libc from glibc-all-in-one for patching by default,for example 2.23.
     \n
     patchup PROGRAM_NAME 2.23\n
     To execute:\n
         patchelf --set-interpreter ./ld-2.23.so ./PROGRAM_NAME\n
         patchelf --replace-needed libc.so.6 ./libc-2.23.so ./PROGRAM_NAME
     """
    arch = pretreatment_arch(program_name)
    success_match = []
    """获取glibc-all-in-one中可用的libc"""
    glibc_path = os.path.abspath('glibc-all-in-one')
    if debug:
        log_debug('glibc_path', glibc_path)
    all_files = [f for f in os.listdir(glibc_path + '/libs')]
    if debug:
        log_debug('all_files', all_files)

    """判断所给的libc是glibc-all-in-one中的数字版本还是指定的一个libc文件名"""
    if not is_number(libc_edition):
        ld_path = match_linker(libc_edition, arch, all_files, glibc_path, debug)
        libc = os.path.abspath(libc_edition)

    else:
        for i in all_files:
            if arch in i:
                if libc_edition in i:
                    success_match.append(i)
        if not success_match:
            """如果没有在libs目录中找到对应libc版本，则去list里面看是否存在所需版本"""
            value = match_libc(glibc_path, libc_edition, arch, success_match)
            if value:
                success_match.append(download_libc(glibc_path, value, debug))
            else:
                log_w("{} not in glibc all in one".format(libc_edition))
                exit()
        log('success_match', success_match)
        libc_index=0
        if choice:
            try:
                libc_index = int(raw_input("Enter the index to select the libc library you want\n"))
            except:
                libc_index = int(input("Enter the index to select the libc library you want\n"))
            if libc_index<0 or libc_index>=len(success_match):
                log_w('invalid index')
                exit()
        libc_path = glibc_path + '/libs/' + success_match[libc_index]
        ld_path = libc_path + '/ld-' + libc_edition + '.so'
        libc = libc_path + '/libc-' + libc_edition + '.so'

        log('libc_matched', libc)
        log('ld_patch', ld_path)
        log('libc_path', libc_path)

    if backup:
        if debug:
            log_debug("cp {} {}".format(program_name, program_name + '.bk'))
        os.system("cp {} {}".format(program_name, program_name + '.bk'))
        log_info("Backup succeeded!")
    if debug:
        log_debug("patchelf --set-interpreter {} {}".format(ld_path, './' + program_name))
        log_debug("patchelf --replace-needed libc.so.6 {} {}".format(libc, './' + program_name))

    os.system("patchelf --set-interpreter {} {}".format(ld_path, './' + program_name))
    os.system("patchelf --replace-needed libc.so.6 {} {}".format(libc, './' + program_name))
    log_info("Use ldd to check whether execute 'patchelf' successfully!\n")
    log_info("The output of ldd:")
    os.system("ldd {}".format(program_name))

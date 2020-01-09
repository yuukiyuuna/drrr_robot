# -*- coding=utf-8 -*-
import time, threading, re, logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains

'''
暂时仅在主线程的处理文本时使用支线程处理，支线程内没有再调用支线程（代码已留，函数interact内，未验证是否报错）
该版本仅支持了播放音乐，后续需要新增发送函数（需要修改send_music函数）
'''

#错误记录
def error_log(e, message):
    logging.basicConfig(level=logging.INFO,
                        filename='Error.log',
                        format='%(asctime)s - %(message)s')
    logging.exception(e)
    logging.info('错误语句：\n' + message)
    logging.info('----------------------------------------------')

#预留函数--处理用户发送的互动消息，从库中找出对应的再返回（为以后庞大的对话库做准备，虽然不知道能不能用得上）
def interact(contant, homeid):
    if contant[0] == '@link':
        con = '资料库内对话'
    elif contant[0] == '\\version':
        con = open('version', 'r').read()
    elif contant[0] == '\\点歌':
        search_music(contant[1], homeid)
        # processing_music = threading.Thread(target=music(contant[1], homeid))
        # processing_music.start()
    else:
        print('interact什么都没匹配到')

#多线程1，处理主线程返回的消息
def retype(message, homeid):
    #处理消息类型
    lastmessage = ''       #预声明最后需要发表的文本
    if re.search(r'"type"', message):
        type = re.search(r'(?<="type":").*?(?=")', message).group()
        name = re.search(r'(?<="name":").*?(?=")', message).group()
        # 根据不同的消息类型来进行不同的操作
        if type == 'message':
            message = message.encode('utf-8').decode('unicode-escape')
            content = re.search(r'(?<="message":").*?(?=")', message).group()
            #如果关键字匹配为命令，则调用order来进行处理
            if re.search(r'@link', content) or re.search(r'\\', content):
                #
                interact_message = content.split(' ', maxsplit=1)
                interact(interact_message, homeid)
        elif type == 'join':
            lastmessage = '@' + name + ' 欢迎光临'

#网易云查找歌曲返回外链
def search_music(name, homeid):
    driver_music = webdriver.Chrome(executable_path="C:\Windows\System32\chromedriver.exe")
    driver_music.get('https://music.163.com/#/search/m/?s= ' + str(name) + '&type=1')
    #因为网易云搜索的结果在frame标签中，需要切换至frame标签中
    driver_music.switch_to.frame('g_iframe')
    #通过正则找出第一个
    music_id = re.search(r'(?<=<a id="song_).*?(?=")', driver_music.page_source).group()
    driver_music.quit()
    #将链接组合成外链形式
    music_url = 'https://music.163.com/#/song/' + str(music_id) + '/'
    send_music(name, music_url, homeid)

def send_music(name, url, homeid):
    #获取当前接收新消息的窗口句柄
    now_handle = driver_drr.current_window_handle
    #新建一个窗口，用于发送歌曲信息
    sendjs = 'window.open("https://drrr.com/room/?id=' + homeid + '");'
    driver_drr.execute_script(sendjs)
    #获取当前所有窗口句柄，用于判断并切换新窗口
    handles = driver_drr.window_handles
    for handle in handles:
        if handle != now_handle:
            # 切换到新打开的窗口B
            driver_drr.switch_to.window(handle)
            #执行命令
            driver_drr.find_element_by_id('musicShare').click()
            driver_drr.find_element_by_id('form-room-music-name').send_keys(name)
            driver_drr.find_element_by_id('form-room-music-url').send_keys(url)
            driver_drr.find_element_by_class_name('btn-sm').click()
            #命令执行成功后关闭新建的窗口，并切换回原本的窗口
            driver_drr.close()
            driver_drr.switch_to.window(handles[0])

def drrr_login(username):
    url = 'https://drrr.com/'
    driver_drr.get(url)
    time.sleep(1.5)

    driver_drr.find_element_by_name('name').send_keys(username)
    time.sleep(0.05)
    driver_drr.find_element_by_name('login').click()
    time.sleep(1.5)

    #进入已知的房间
    # driver_drr.get('https://drrr.com/room/?id=w18Tgy4HOE')
    # time.sleep(1.5)

def make_home(name, description, limit, music):
    driver_drr.find_element_by_xpath('//*[@id="create_room"]').click()
    time.sleep(0.2)
    driver_drr.find_element_by_id('form-user-name').send_keys(name)     #房间名称
    time.sleep(0.2)
    driver_drr.find_element_by_id('form-room-description').send_keys(description)       #房间描述
    time.sleep(0.2)
    # driver_drr.find_element_by_id('form-user-limit').send_keys(limit)   #成员人数
    # time.sleep(0.2)
    if music == 1:
        driver_drr.find_element_by_id('form-user-music').click()        #是否开启音乐房间
    time.sleep(1)
    driver_drr.find_element_by_xpath('//*[@id="body"]/div/div[1]/div/form/div[8]/input').click()
    time.sleep(1)
    #将房间ID传回主函数中，用于发消息和点歌的请求页面中
    get_url = str(driver_drr.current_url)
    homeid = get_url.split('=')[1]
    return homeid

#定义全局变量，使所有操作可以在一个浏览器窗口内进行
global driver_drr
driver_drr = webdriver.Chrome(executable_path ="C:\Windows\System32\chromedriver.exe")
driver_drr.implicitly_wait(10)

#注册账号并进入房间
username = 'happyhoney'
homename = '快乐听歌连天'
description = '边听歌边聊天吧，niconiconi'
limit = '5'
music = int('1')


try:
    drrr_login(username)
except Exception as e:
    error_log(e, '登入失败，程序退出')
    driver_drr.quit()
    sys.exit()

try:
    homeid = make_home(homename, description, limit, music)
except Exception as e:
    error_log(e, '创建房间失败，程序退出')
    driver_drr.quit()
    sys.exit()

#主循环，获取时间戳之后的消息并处理文本
last_time = str(int(time.time()))
# last_time_old = '1'
while 1:
    # 因为子线程会切换浏览器句柄，该try一定会在切换句柄的时候报错，所以此处暂不记录报错日志
    try:
        driver_drr.get('https://drrr.com/json.php?update=' + last_time)
        messages = driver_drr.find_element_by_xpath('/html/body').text

        # 获取文本中最后的时间戳，然后用这个时间戳请求内容
        update_time = re.findall(r'(?<="time":).*?(?=,)', messages)
        #判断是否能读取到时间，读取不到则换下一个关键词
        if len(update_time) == 0:
            update_time = re.findall(r'(?<="update":).*?(?=,)', messages)

        last_time = update_time[len(update_time) - 1]
        '''     有了新的办法，所以该方法弃用留于备份用
        #判断是否有消息更新，若没有新消息则跳过循环
        if float(last_time) - float(last_time_old) == 0.01:
            time.sleep(3)
            last_time_old = last_time
            last_time = str(float(last_time) + 0.01)
            print('程序跳过一次完成')
            continue
    '''
        last_time = str(float(last_time) + 0.01)

        # 处理文本内容,将文本扔给支线程处理
        messages_new = messages.split('},{')
    except Exception as e:
        time.sleep(3)
        continue
    try:
        for a in range(0, len(messages)):
            processing_text = threading.Thread(target=retype(messages_new[a], homeid))
            processing_text.start()
    except Exception as e:
        error_log(e, messages)

    time.sleep(3)



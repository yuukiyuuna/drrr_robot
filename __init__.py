# -*- coding=utf-8 -*-
import time, threading, re, logging, sys
from selenium import webdriver


#第一子线程，用于接收更新的消息数据，将消息处理后传给第二子线程（识别消息）
def get_content():
    global messages_save
    global driver_drr
    last_time = str(int(time.time()) - 15)
    while 1:
        # 因为子线程会切换浏览器句柄，该try一定会在切换句柄的时候报错，所以此处暂不记录报错日志
        try:
            lock.acquire()
            driver_drr.get('https://drrr.com/json.php?update=' + last_time)
            messages = driver_drr.find_element_by_xpath('/html/body').text
            lock.release()
            messages = messages.encode('utf-8').decode('unicode-escape')

            # 获取文本中最后的时间戳，然后用这个时间戳请求内容
            update_time = re.findall(r'(?<="time":).*?(?=,)', messages)

            # 如果能获取时间戳，则请求该时间戳+0.01的之后的内容，避免获取重复时间
            #因为刚创立房间不会有time字段，而会有uptime字段，所以如果没有time字段则不改变请求时间
            if len(update_time) != 0:
                update_time = re.findall(r'(?<="update":).*?(?=,)', messages)
            else:
                time.sleep(3)
                print('没有获取到新的时间，第一子线程已跳过')
                print('----------------------------------------')
                continue

            # 将请求的时间加上0.01秒，避免再次处理上次已处理的请求
            last_time = update_time[len(update_time) - 1]
            last_time = last_time.replace('}', '')          #在测试时有的时间会有{，需要去掉
            last_time = str(float(last_time) + 0.01)
            print('请求时间为：' + last_time)

            # 处理文本内容,将文本扔给支线程处理
            if messages.find('},{') != -1:
                # 在写入变量的时候锁住该变量，防止第二子进程写入
                a = messages.split('},{')
                lock.acquire()
                for b in a:
                    messages_save.append(b)
                print('以获取全局变量messages_save:' + str(messages_save))
                lock.release()
            elif messages.find(':[{') != -1:
                # 在写入变量的时候锁住该变量，防止第二子进程写入
                a = messages.split(':[{')
                lock.acquire()
                for b in a:
                    messages_save.append(b)
                print('以获取全局变量messages_save:' + str(messages_save))
                lock.release()
            else:
                # print('未获取全局变量messages_save，第一子线程已跳过')
                # print('----------------------------------------')
                time.sleep(3)
                continue
        except Exception as e:
            error_log(e, '已获取问题语句：' + messages)
            time.sleep(3)
            continue
        print('----------------------------------------')
        time.sleep(3)

#第二子线程，用于识别消息里的命令语句，然后进行处理
def process_content():
    # 在这里组合如果被@的名字组合：
    global messages_save
    global music_name
    myname = '@' + username
    message_list = []
    while 1:
        # 判断是否有未处理的消息，如果没有跳过循环
        try:
            lock.acquire()
            message_list = messages_save
            messages_save = []
            lock.release()
            if len(message_list) != 0:
                # 在读取messages_save函数内容期间，使用进程所将该函数锁住
                # 若message_save有内容，获取该内容并重置该变量
                print('message_list变量已被获取:' + str(message_list))
                pass

                # print('----------------------------------------')
            else:
                # print('message_save变量未被获取，第二子进程已经跳过')
                # print('----------------------------------------')
                time.sleep(0.2)
                continue
        except Exception as e:
            error_log(e, '传递获取到的消息的时候失败（第一子线程给第二子线程传递参数后处理失败）')
            continue

        #处理获取到的数组
        try:
            for message in message_list:
                lastmessage = ''  # 预声明最后需要发表的文本
                if re.search(r'"type"', message):
                    type = re.search(r'(?<="type":").*?(?=")', message).group()
                    name = re.search(r'(?<="name":").*?(?=")', message).group()
                    share =  re.findall('"url":"http.*?\.mp3"', message)
                    # 根据不同的消息类型来进行不同的操作
                    #如果匹配到时消息类型的话
                    if type == 'message' and len(share) == 0:
                        content = re.search(r'(?<="message":").*?(?=")', message).group()
                        # 如果关键字匹配为命令，则调用order来进行处理
                        #如果匹配到相关命令的语句的时候
                        if re.search(myname, content) or re.search(r'\\', content):
                            #以第一个空格进行切分
                            order = content.split(' ', maxsplit=1)
                            # print('已配到类似命令的语句：' + str(order))
                            if order[0] == myname:
                                print('匹配资料库进行对话')
                            elif order[0] == '\\点歌':
                                # print('已点歌曲：' + order[1])
                                lock.acquire()
                                music_name.append(order[1])
                                lock.release()
                            elif order[0] == '\\version':
                                reply = open('version', 'r').read()
                                print('当前版本：' + str(reply))
                    elif type == 'join':
                        sendmessage = '@' + name + ' 欢迎光临'
                        print(sendmessage)
        except Exception as e:
            error_log('e', '处理消息的过程中失败：\n' + str(message_list))
            continue

#第三子线程，用于查找歌曲名称并直接向房间内分享音乐
def music():
    global music_name
    global send_messages
    music_list = []
    while 1:
        lock.acquire()
        music_list = music_name
        music_name = []
        lock.release()

        try:
            if len(music_list) == 0:
                # print('未获取需要查找的歌曲名，第三子线程已跳过')
                # print('----------------------------------------')
                time.sleep(5)
                continue
            else:
                driver_music = webdriver.Chrome(executable_path="C:\Windows\System32\chromedriver.exe")
                for name in music_list:
                    try:
                        # 循环前先把musciid重置，避免未找到歌曲的时候继续使用上一个id
                        driver_music.get('https://music.163.com/#/search/m/?s= ' + str(name) + '&type=1')
                        # 因为网易云搜索的结果在frame标签中，需要切换至frame标签中
                        driver_music.switch_to.frame('g_iframe')
                        # 通过正则找出第一个
                        music_id = re.search(r'(?<=<a id="song_).*?(?=")', driver_music.page_source).group()
                        # 将链接组合成外链形式
                        music_url = 'https://music.163.com/#/song/' + str(music_id) + '/'
                        # print('已查到歌曲外链地址：' + music_url)
                        # 第一字段的1表示为分享音乐，第二字段的name表示歌曲id，第三字段的url表示歌曲外链
                        text = [1, music_id, music_url]
                        lock.acquire()
                        send_messages.append(text)
                        # print(send_messages)
                        lock.release()
                    except Exception as e:
                        error_log(e, '获取歌曲外链的时候失败，失败歌曲名字为：' + str(name))
                driver_music.quit()
        except Exception as e:
            error_log(e, '获取歌曲外链时出错,歌曲名城为：' + str(music_list))
            time.sleep(1)
        # print('----------------------------------------')

#第四子线程，用于发送消息与歌曲外链的
def process_send():
    global send_messages
    global homeid

    while 1:
        try:
            lock.acquire()
            send_contant = send_messages
            send_messages = []
            lock.release()
            if len(send_contant) == 0:
                # print('未获取需要发送的消息内容，第四子线程已跳过')
                # print('----------------------------------------')
                time.sleep(5)
                continue
            else:
                # print('已获取到需要发送的消息内容：' + str(send_contant))
                for message in send_contant:
                    # messages[0]为需要发送文本消息
                    if message[0] == 0:
                        # print('发送系统消息')
                        # print('----------------------------------------')
                        pass
                    # messages[1]为需要点歌
                    elif message[0] == 1:
                        lock.acquire()
                        now_handle = driver_drr.current_window_handle
                        # 新建一个窗口，用于发送歌曲信息
                        sendjs = 'window.open("https://drrr.com/room/?id=' + homeid + '");'
                        driver_drr.execute_script(sendjs)
                        # 获取当前所有窗口句柄，用于判断并切换新窗口
                        handles = driver_drr.window_handles
                        for handle in handles:
                            if handle != now_handle:
                                # 切换到新打开的窗口B
                                driver_drr.switch_to.window(handle)
                                # 执行命令
                                driver_drr.find_element_by_id('musicShare').click()
                                driver_drr.find_element_by_id('form-room-music-name').send_keys(message[1])
                                driver_drr.find_element_by_id('form-room-music-url').send_keys(message[2])
                                time.sleep(0.1)
                                driver_drr.find_element_by_class_name('btn-sm').click()
                                # 命令执行成功后关闭新建的窗口，并切换回原本的窗口
                                driver_drr.close()
                                driver_drr.switch_to.window(handles[0])
                        lock.release()
        except Exception as e:
            error_log(e, '发送消息失败，消息为：' + str(send_contant))

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

#用于记录错误日志，记录在脚本所在文件夹下的error.log中
def error_log(e, message):
    logging.basicConfig(level=logging.INFO,
                        filename='error.log',
                        format='%(asctime)s - %(message)s')
    logging.exception(e)
    logging.info('错误消息：\n' + message)
    logging.info('----------------------------------------------')




global messages_save        #第一子线程将捕获的数据放置该变量中，供第二子线程读取该数据
global music_name           #第二子线程将歌曲名放置在该函数中
global send_messages        #保存需要发送的文本
global homeid
global username
global lock                 #线程锁
global driver_drr           #定义全局变量，使所有操作可以在一个浏览器窗口内进行
lock = threading.RLock()
driver_drr = webdriver.Chrome(executable_path ="C:\Windows\System32\chromedriver.exe")
driver_drr.implicitly_wait(10)
messages_save = []
music_name = []
send_messages = []


#注册账号并进入房间
username = '青空云之彼方'
homename = '苍天之上'
description = '边听歌边聊天吧，niconiconi'
limit = '5'
musicname = int('1')

#登入drrr并注册账号
try:
    drrr_login(username)
except Exception as e:
    error_log(e, '登入失败，程序强制退出')
    driver_drr.quit()
    sys.exit()

#创建房间
try:
    homeid = make_home(homename, description, limit, musicname)
except Exception as e:
    error_log(e, '创建房间失败，程序退出')
    driver_drr.quit()
    sys.exit()

#t1为获取新消息
t1 = threading.Thread(target=get_content)
t2 = threading.Thread(target=process_content)
t3 = threading.Thread(target=music)
t4 = threading.Thread(target=process_send)

t1.start()
t2.start()
t3.start()
t4.start()

t1.join()
t2.join()
t3.join()
t4.join()
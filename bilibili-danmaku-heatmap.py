#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, requests
import numpy as np

try:
    # Python 2.7 兼容性 Hack
    reload(sys)
    sys.setdefaultencoding('utf8')
except:
    # 正运行在 Python 3 上
    def raw_input(prompt):
        return input(prompt)

# 全局设置
cfg = {
    # 获取弹幕池 ID 方式
    # - pagelist : 通过 http://www.bilibili.com/widget/getPageList API
    #   (视频标题可能无法正确显示)
    # - webpage : 通过视频播放网页
    #   (分P数量及分P标题可能无法正确显示)
    # - both : 两者兼用
    #   (多一个 HTTP 请求)
    'getDmidFrom' : 'both',
    # 弹幕统计时间跨度
    # - 小于0: 设置为视频长度的相应除数，例如 -2 代表视频长度的 1/2，-3 代表 1/3
    # - 等于0: 设置为视频长度的 1/25
    # - 大于0: 设置为相应秒数，例如 2 代表 2 秒
    'timespan' : 5
}
requestHeader = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
}
# 主要代码开始

def stripStr(source, startFrom, endAt):
    posStart = source.find(startFrom)
    if(posStart == -1):
        return False
    posStart += len(startFrom)
    posStop = source.find(endAt, posStart)
    if(posStop == -1):
        return False
    return source[posStart : posStop]

def inputDigit(notification, minValue = 0, maxValue = 2147483647):
    n = str(raw_input(notification))
    flag = True
    if(not n.isdigit()):
        flag = False
    else:
        if(int(n) < minValue or int(n) > maxValue):
            flag = False
    while(not flag):
        print('- ! 您的输入不符合要求')
        n = raw_input(notification)
        flag = True
        if(not n.isdigit()):
            flag = False
        else:
            if(n < minValue or n > maxValue):
                flag = False
    return int(n)

def processDMLine(dmLine):
    dmMetaStart = dmLine.find('"') + 1
    dmMetaEnd = dmLine.find('"', dmMetaStart)
    dmMeta = dmLine[dmMetaStart : dmMetaEnd].split(',')
    dmData = {
        'pos' : float(dmMeta[0]),   # 时间轴坐标
        'sender' : dmMeta[6],       # sender id
        'dbid' : int(dmMeta[7]),    # database id
        'time' : int(dmMeta[4]),    # time danmaku sent
        'text' : dmLine[dmLine.find('">') + 2 : -4]
    }
    if(int(dmMeta[1]) >= 1 and int(dmMeta[1]) <= 3):
        dmData['type'] = 'standard'
    elif(int(dmMeta[1]) == 4):
        dmData['type'] = 'bottom'
    elif(int(dmMeta[1]) == 5):
        dmData['type'] = 'top'
    elif(int(dmMeta[1]) == 6):
        dmData['type'] = 'reverse'
    elif(int(dmMeta[1]) == 7):
        dmData['type'] = 'advanced'
    elif(int(dmMeta[1]) == 8):
        dmData['type'] = 'code'
    else:
        dmData['type'] = dmMeta[1]

    if(int(dmMeta[2]) == 25):
        dmData['size'] = 'normal'
    elif(int(dmMeta[2]) == 18):
        dmData['size'] = 'small'
    else:
        dmData['size'] = dmMeta[2]

    dmData['color'] = str(hex(int(dmMeta[3])))[2:]
    while(len(dmData['color']) < 6):
        dmData['color'] = '0' + dmData['color']

    if(int(dmMeta[5]) == 0):
        dmData['pool'] = 'standard'
    elif(int(dmMeta[5]) == 1):
        dmData['pool'] = 'subtitle'
    elif(int(dmMeta[5]) == 2):
        dmData['pool'] == 'advanced'
    else:
        dmData['pool'] == dmMeta[5]

    return dmData

def exportDM(dmData):
    startPos = dmData.find('<d p=')
    if(startPos == -1):
        return False
    dmData = dmData[startPos : -4]
    dmArray = dmData.replace('</d><d', '</d>\n<d').splitlines()
    response = []
    for dmLine in dmArray:
        response.append(processDMLine(dmLine))
    return response

def smoothify(line, smoothiness = 5):
    oriline = np.array(line)
    newline = np.zeros(len(line))
    for i in range(len(line)):
        for j in range(max(0, i - smoothiness), min(len(line), i + smoothiness + 1)):
            ratio = (1 - 1 / smoothiness * abs(i - j))
            newline[i] += line[j] * ratio
    ratio = max(oriline) / max(newline)
    newline *= ratio
    #print('RATIO: %.4f' % ratio)
    return newline

avID = inputDigit('? 输入视频 av 号: av', 1)
avPage = 0

try:
    if(cfg['getDmidFrom'] == 'pagelist' or cfg['getDmidFrom'] == 'both'):
        # pagelist 方式处理过程
        videoMetaRequest = requests.get('http://www.bilibili.com/widget/getPageList?aid=' + str(avID), headers = requestHeader)
        videoMetaRequest.encoding = 'utf-8'
        if(videoMetaRequest.status_code != 200):
            # Fallback 到 webpage 方式
            print('X 获取 PageList API 失败, 转为直接获取播放页面')
            cfg['getDmidFrom'] = 'webpage'
        else:
            # 默认: 获取分P列表以获取弹幕池 ID
            videoMeta = videoMetaRequest.json()
            if(len(videoMeta) == 1):
                avPage = 1
            else:
                avPage = inputDigit('? 输入视频页码: (1 - %i) #' % len(videoMeta), 1, len(videoMeta))
    if(cfg['getDmidFrom'] == 'webpage' or cfg['getDmidFrom'] == 'both'):
        # webpage 方式处理过程
        if(avPage == 0):
            avPage = inputDigit('? 输入视频页码: #', 1)
        if(avPage == 1):
            videoPageRequest = requests.get('http://www.bilibili.com/video/av' + str(avID) + '/', headers = requestHeader)
            videoPageRequest.encoding = 'utf-8'
            videoPage = videoPageRequest.text
        else:
            videoPageRequest = requests.get('http://www.bilibili.com/video/av' + str(avID) + '/index_' + str(avPage) + '.html', headers = requestHeader)
            videoPageRequest.encoding = 'utf-8'
            videoPage = videoPageRequest.text
except:
    print('X 视频信息获取失败，原因可能是:')
    print('  - 网络连接不稳定')
    print('  - 网络连接中断')
    print('  - Bilibili 服务器出现问题')
else:
    if(cfg['getDmidFrom'] == 'webpage'):
        videoInfo = {
            'title' : stripStr(videoPage, '<title', '</title>').split('>')[1].split('_')[0],
            'id' : avID,
            'dmid' : int(stripStr(videoPage, 'cid=', '&'))
        }
    if(cfg['getDmidFrom'] == 'pagelist'):
        videoInfo = {
            'title': videoMeta[avPage - 1]['pagename'],
            'id': avID,
            'dmid': int(videoMeta[avPage - 1]['cid'])
        }
    if(cfg['getDmidFrom'] == 'both'):
        videoInfo = {
            'title': stripStr(videoPage, '<title', '</title>').split('>')[1].split('_')[0],
            'id': avID,
            'dmid': int(videoMeta[avPage - 1]['cid'])
        }
        if(videoMeta[avPage - 1]['pagename'] != ''):
            videoInfo['title'] += ' - ' + videoMeta[avPage - 1]['pagename']

    print('i 视频标题: ' + videoInfo['title'])
    print('i 视频av号: '+ str(videoInfo['id']))
    print('i 弹幕池号: '+ str(videoInfo['dmid']))

    if(videoInfo['dmid'] == 0):
        # 弹幕池 ID 获取失败
        print('X 视频弹幕池 ID 获取失败，原因可能是:')
        if(cfg['getDmidFrom'] == 'webpage' or cfg['getDmidFrom'] == 'both'):
            if(videoPage.find('http://static.hdslb.com/mstation/images/video/notfound')):
                print('  - 视频被删除')
                print('  - 视频只有会员能观看')
            else:
                print('  - Bilibili 改版, 原获取方式失效')
                print('  - 网络不稳定')
        else:
            print('  - 视频被删除')
            print('  - 视频只有会员能观看')
            print('  - Bilibili 改版, 原获取方式失效')
            print('  - 网络不稳定')
    else:
        dmRequest = requests.get('http://comment.bilibili.com/%i.xml' % videoInfo['dmid'], headers = requestHeader)
        dmRequest.encoding = 'utf-8'
        dmData = exportDM(dmRequest.text)
        maxTime = 0
        for dmLine in dmData:
            maxTime = max((maxTime, dmLine['pos']))
        maxTime = int(maxTime) + 1
        timecount = np.zeros(maxTime)
        for dmLine in dmData:
            dmTime = int(dmLine['pos'])
            timecount[dmTime] += 1
        import matplotlib.pyplot as plt
        from scipy import interpolate
        timeline = np.arange(0, maxTime, 0.1)
        if(cfg['timespan'] == 0):
            timespan = int(maxTime / 25)
        elif(cfg['timespan'] < 0):
            timespan = int(maxTime / (-cfg['timespan']))
        else:
            timespan = cfg['timespan']
        plt.plot(timeline, interpolate.splev(timeline, interpolate.splrep(range(maxTime), smoothify(timecount, timespan))), 'b-',
            range(maxTime), timecount, 'b.')
        plt.title('%s\nav%i 弹幕池号%i +/-%is' % (videoInfo['title'], videoInfo['id'], videoInfo['dmid'], timespan))
        plt.xlabel('时间轴')
        plt.ylabel('弹幕量')
        plt.axis([0, maxTime, 0, max(timecount)])
        plt.show()

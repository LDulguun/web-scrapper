from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import csv
import time
import timeit
import wget
import os
import urllib.request as urllib2
import re

DRIVER_PATH = '../chromedriver'

options = Options()
options.headless = True
options.add_argument("--window-size=1920,1200")

driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)

def formatName(name) :
    name = name.replace('/', ' ')
    name = name.replace('"', ' ')
    name = name.replace('\\', ' ')
    name = name.replace(':', ' ')
    name = name.replace('|', ' ')
    name = name.replace('<', ' ')
    name = name.replace('>', ' ')
    name = name.replace('*', ' ')
    name = name.replace('?', ' ')

    while (name[-1] == ' ' or name[-1] == '.') :
        name = name[:-1]

    return name

def listToCSV(l, filename) :
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows([list(l)])

def CSVtoList(filename) :
    with open(filename, newline='') as file:
        reader = csv.reader(file)
        return list(reader)[0]

def getHtml(url, retries=5):
    try:
        html = urllib2.urlopen(url, timeout=60).read()
    except Exception:
        if retries > 0:
            print('retry')
            return getHtml(url, retries - 1)
    return html

def crawlMainPage2() :
    hrefs = set()
    gridClassName = "outfit-grid"
    
    driver.get('https://www.zalando.co.uk/get-the-look-women/')
    
    #scroll through the page because the page is generated dynamically
    speed = 10
    current_scroll_position, new_height= 0, 1
    while current_scroll_position <= new_height:
        current_scroll_position += speed
        driver.execute_script("window.scrollTo(0, {});".format(current_scroll_position))
        new_height = driver.execute_script("return document.body.scrollHeight")

    html = driver.page_source
    reg = r'<a class=\"_2zkIHA Mpbpu9 lre9zn hoxwwN _8Nfi4s _2zkIHA\" href=\"(.*?)\" .*?</a>'
    regComp = re.compile(reg)
    hrefList = re.findall(regComp, html)

    for href in hrefList :
        hrefs.add('https://www.zalando.co.uk' + href)

    return hrefs

def crawlStylePage(href) :
    #example link https://www.zalando.co.uk/outfits/TX031U5gSku/
    username = ""
    imgsrcs = set()
    similar = set()
    itemHrefs = set()

    html = getHtml(href)

    reUsername = re.compile(rb'<span class=\"A95iT1 pDVUjz nmA88J NNECXo AHAcbe x--xNS A_8GRa vDA-c4 HWFFx9 _9u_0uT BQJRnm\">(.*?)</span>')
    username = re.findall(reUsername, html)
    if (len(username) == 0) :
        return '', {}, {}, {}
    username = formatName(username[0].decode("utf-8"))
    regexp = re.compile(r'alando')  # skip the page if it is not a valid user
    if regexp.search(username):
        return '', {}, {}, {}
    
    reImgs = re.compile(rb'<li class=\"_98z9Z5 _4ypdpr Wqd6Qu\">.*?(https://.*?/outfit-image-mhq/.*?\..*?)\?.*?</li>')
    imgListb = re.findall(reImgs, html)
    for imgb in imgListb :
        imgsrcs.add(imgb.decode("utf-8"))

    reHrefs = re.compile(rb'<a class=\"_2zkIHA Mpbpu9 lre9zn hoxwwN _8Nfi4s _2zkIHA\" href=\"(.*?)\".*?</a>')
    hrefbList = re.findall(reHrefs, html)
    for hrefb in hrefbList :
        similar.add('https://www.zalando.co.uk' + hrefb.decode("utf-8"))
    
    reHrefs = rb'<a class=\"_2zkIHA Mpbpu9 lre9zn hoxwwN _8Nfi4s _2zkIHA auWjdQ _70SxGu kmttEr _8UdArp\" href=\"(.*?)\" rel="">.*?</a>'
    reHrefsComp = re.compile(reHrefs)
    hrefbList = re.findall(reHrefsComp, html)
    for hrefb in hrefbList :
        itemHrefs.add(hrefb.decode("utf-8"))

    return username, imgsrcs, similar, itemHrefs

def crawlItemPage(href) :       #output : text, imgsrcs
    #example link https://www.zalando.co.uk/jcrew-taryn-leafy-trousers-purple-green-jc421a028-i11.html
    driver.get(href)
    name = ""
    text = ""
    links = set()
    xpathTitle = '/html/body/div[4]/div/div[1]/div/div[2]/x-wrapper-re-1-2/h1'
    xpathDetails = '/html/body/div[4]/div/div[1]/div/div[2]/div[3]/div/div[1]/div[2]/div[2]/div'
    xpathImages = '/html/body/div[4]/div/div[1]/div/div[1]/x-wrapper-re-1-1/div/div[1]/div/div/div/ul/li/div/button/div/div/img'
    
    try :
        element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, xpathTitle))
        )
        name = formatName(element.get_attribute("innerText"))
        text = name + "\n"

        element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, xpathDetails))
        )
        divs = element.find_elements_by_xpath('.//div')
        for div in divs :
            text = text + div.find_element_by_xpath('.//span[1]').get_attribute("innerText") + " "
            text = text + div.find_element_by_xpath('.//span[2]').get_attribute("innerText") + "\n"
        text += "\n"

        elements = driver.find_element(By.XPATH, '/html/body/div[4]/div/div[1]/div/div[1]/x-wrapper-re-1-1').find_elements(By.XPATH, './/img')
        for element in elements :
            links.add(element.get_attribute("src")[:113])
    finally :
        return name, text, links

def saveStyleHrefsToCSV(filename) :
    start = timeit.default_timer()
    hrefsList = crawlMainPage2()
    listToCSV(hrefsList, filename)
    stop = timeit.default_timer()
    print('It took : ', stop - start, ' seconds')
    print('Total of ', len(hrefsList), ' hrefs collected')

def mainf() :
    q = CSVtoList('hrefsFinal2.csv')    #queue for iteration
    hrefSet = set(q)

    mainPath = 'D:/NTU/ASTAR Project/zalandoFinale'
    counter = {}
    progress = 0
    validStyles = 0

    while (len(q) > 0) :
        styleHref = q[0]
        print(styleHref)        #debug
        progress += 1
        print(str(progress) + '/' + str(len(hrefSet)))      #check progress
        username, imgsrcs, similar, itemHrefs = crawlStylePage(styleHref)

        if (username != '') :
            validStyles += 1
            print(validStyles)          #check progress

            userPath = mainPath + '/' + username
            isExists = os.path.exists(userPath)
            if (not isExists) :
                os.makedirs(userPath)

            if (username not in counter) :
                counter[username] = 0

            for link in similar :
                if link not in hrefSet :
                    hrefSet.add(link)
                    q.append(link)     # add new links to the queue

            counter[username] += 1
            stylePath = userPath + '/' + str(counter[username])
            isExists = os.path.exists(stylePath)
            if (not isExists) :
                os.makedirs(stylePath)

            for imgsrc in imgsrcs :
                try :
                    wget.download(imgsrc, stylePath)
                except :
                    pass

            description = open(stylePath + '/' + 'description.txt', 'a+')

            for itemHref in itemHrefs :
                itemName, text, itemImgSrcs = crawlItemPage(itemHref)
                description.write(text)
                isExists = os.path.exists(stylePath + '/' + itemName)
                if (not isExists) :
                    os.makedirs(stylePath + '/' + itemName)
                for itemImgSrc in itemImgSrcs :
                    try :
                        wget.download(itemImgSrc, stylePath + '/' + itemName)
                    except :
                        pass
            description.close()
        q.pop(0)    #remove checked link from the queue

mainf()

'''
username, imgsrcs, similar, itemHrefs = crawlStylePage('https://www.zalando.co.uk/outfits/oQ-2uLYWSdq')
print([username])

print(imgsrcs)
'''

'''
username, imgsrcs, similar = crawlItemPage('https://www.zalando.co.uk/nly-by-nelly-puffy-power-sequin-dress-cocktail-dress--party-dress-gold-neg21c06q-f11.html')

print(username)
print(imgsrcs)
print(similar)
'''

driver.quit()
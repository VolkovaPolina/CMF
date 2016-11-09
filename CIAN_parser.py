# -*- coding: utf-8 -*-
"""
Created on Sat Nov  3 10:15:02 2016
CIAN parser
"""
#Загрузка необходимых пакетов
import pandas as pd
import requests 
import re    
from bs4 import BeautifulSoup   
import math 


print (pd.__version__)
#Будем использовать регулярные выражения 
def html_stripper(text):
    return re.sub('<[^<]+?>', '', str(text))
    
#Ссылка верхнего уровня, в параметре &p передается номер страницы
district = 'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=13&district%5B1%5D=14&district%5B2%5D=15&district%5B3%5D=16&district%5B4%5D=17&district%5B5%5D=18&district%5B6%5D=19&district%5B7%5D=20&district%5B8%5D=21&district%5B9%5D=22&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1'

#Загрузим ссылки на все страницы 
links = []
for page in range(1, 30):
    page_url = district.format(page) 
    search_page = requests.get(page_url) #загрузка страницы
    search_page = search_page.content
    search_page = BeautifulSoup(search_page, 'lxml') # разбиваем страницу на блоки
    
    flat_urls = search_page.findAll('div', attrs = {'ng-class':"{'serp-item_removed': offer.remove.state, 'serp-item_popup-opened': isPopupOpen}"})
    flat_urls = re.split('http://www.cian.ru/sale/flat/|/" ng-class="', str(flat_urls)) #разделяем ссылку на части 
    
    for link in flat_urls:
        if link.isdigit():
            links.append(link)

flatStats = {} #для записи в конечную таблицу 
           
#ссылка на квартиру состоит из следующих частей:'http://www.cian.ru/sale/flat/' + links[i] + '/'

#ЧИСЛО КОМНАТ 
def getRoom(flat_page):
    rooms = flat_page.find('div', attrs={'class':'object_descr_title'})
    rooms = html_stripper(rooms)
    try:
        rooms = re.findall(r'\d+-комн', rooms)[0] #sometimes there are 10+ rooms, so d+
        rooms = re.findall(r'\d+', rooms)[0]
        flatStats['Rooms'] = int(rooms)
    except:
        flatStats['Rooms'] = 'NA'

#ЦЕНА
def getPrice(flat_page):
    price = flat_page.find('div', attrs={'id':'price_rur', 'style':'display: none;visibility: hidden;'})
    price = html_stripper(price)
    price = price.replace(',', '.')
    flatStats['Price']  = int(float(price))

#Будем использовать готовую таблицу на сайте для оптимизации кода 
    
def getTableInformation(flat_page):
    table = flat_page.find('table', attrs={'class':'object_descr_props flat sale', 'style':'float:left'})
    table = html_stripper(table)
    
    
    #ОБЩАЯ ПЛОЩАДЬ 
    Totsp  = re.split('Общая площадь:\n\n|\xa0м2', table)[1]
    Totsp = Totsp.replace(',', '.')
    if re.search(r'(–|-)', Totsp): flatStats['Totsp'] = 'NA'
    else:
        flatStats['Totsp'] = float(Totsp)
    #ЖИЛАЯ ПЛОЩАДЬ 
    Livesp = re.split('Жилая площадь:\n\n|\xa0м2\n\n\n\nПлощадь кухни:', table)[1]
    Livesp = Livesp.replace(',', '.')
    if re.search(r'(–|-)', Livesp): flatStats['Livesp'] = 'NA'
    else:
        flatStats['Livesp'] = float(Livesp)
    
    #ПЛОЩАДЬ КУХНИ
    Kitsp = re.split('Площадь кухни:\n\n|\n\n\nСовмещенных санузлов:', table)[1]
    Kitsp = Kitsp.replace(',', '.')
    if re.search(r'(–|-)', Kitsp): flatStats['Kitsp'] = 'NA'
    else:
        Kitsp = re.findall('(\d+.\d+|\d+)', Kitsp)[0]
        flatStats['Kitsp'] = float(Kitsp)
    
    #ТИП ДОМА
    Type = (re.split('Тип дома:\n\n|\n\n\nТип продажи:', table)[1])
    if re.search(r'(монолит|кирпич|жб|желез)', Type): flatStats['Brick']=1
    else: flatStats['Brick']=0
    if re.search('новостр', Type): flatStats['New']=1
    else: flatStats['New']=0
        
    #ТЕЛЕФОН
    if re.search('Телефон', table):
        Tel = re.split('Телефон:\n|\n\n\nВид из окна:', table)[1]
        if re.search(r'(нет|–|-)', Tel): flatStats['Tel'] = 0
        else: flatStats['Tel'] = 1
    else: flatStats['Tel'] = 'NA'
        
    #БАЛКОН
    Bal = re.split('Балкон:\n|\n\n\nЛифт:', table)[1]
    if re.search(r'(нет|–|-)', Bal): flatStats['Bal'] = 0
    else: flatStats['Bal']=1
        

    #НОМЕР ЭТАЖА + ВСЕГО ЭТАЖЕЙ В ДОМЕ
    floors = (re.split('Этаж:\n\n|Тип дома', table)[1])
    floors = re.findall('(\d+)', floors)
    flatStats['Floor'] = int(floors[0])
    #если нет информации
    try:
        flatStats['Nfloors'] = int(floors[1])
    except IndexError:
        flatStats['Nfloors'] = 'NA'
   

#РАССТОЯНИЕ ДО ЦЕНТРА 
def getCoords(flat_page):
    coords = flat_page.find('div', attrs={'class':'map_info_button_extend'}).contents[1]
    coords = re.findall(r'\d+\.\d+', str(coords) )
    lat, lon = float(coords[0]), float(coords[1])
    Mlat, Mlon = 55.753709,  37.619813
    dist = math.sqrt( (Mlat-lat)**2 + (Mlon-lon)**2 ) # still can not find information how to convert this to km
    flatStats['lat'], flatStats['lon'], flatStats['Dist'] = lat, lon, dist


#РАССТОЯНИЕ ДО МЕТРО
def getMetro(flat_page):
    try:
        metro = flat_page.find('a', attrs={'class':'object_item_metro_name', 'target':'_blank', 'rel':'nofollow'})
        metro = metro.contents[0]
    
        metrdist = flat_page.find('span', attrs={'class':'object_item_metro_comment'}).contents[0]
        Metrdist = int(re.findall(r'\d+', metrdist)[0])
        if re.search('пешком', metrdist): Walk = 1 #may be there are another key words, but I can not find
        else: Walk = 0
    except:
        Walk, Metrdist = 'NA', 'NA'
        
    flatStats['Metrdist'] = Metrdist
    flatStats['Walk'] = Walk

#Цикл для всех квартир 

Flats = pd.DataFrame()
for i in range(len(links)):
    
    flat_url = 'http://www.cian.ru/sale/flat/' + links[i] + '/'
    flat_page = requests.get(flat_url)
    flat_page = flat_page.content
    flat_page = BeautifulSoup(flat_page, 'lxml')
    
    getPrice(flat_page)
    getCoords(flat_page)
    getRoom(flat_page)
    getMetro(flat_page)
    getTableInformation(flat_page)
    
    Flats = Flats.append(flatStats, ignore_index=True)
    
    if not i%50:
        print('working on flat number {}'.format(i) ) 
    
    
#Записываем итоговый файл csv
Flats.to_csv('flats_CIAN.csv', index=True)
    
    
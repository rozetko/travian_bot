#!/usr/bin/env python
# encoding: utf-8

''' TODO:
- don't delete everything when building resource fields and reach max lvl
- upgrade warehouse/granary if not enough space
- upgrade crop fields if not enough free crop
- farm
- waiting while building is upgrading
- check hero HP before adventure
'''

import json, os.path, logging, sys
from urllib2 import *
from datetime import *
from cookielib import CookieJar
from urllib import urlencode
from urlparse import urljoin
from bs4 import BeautifulSoup
from threading import Thread
from time import sleep
from re import findall, search
from math import pow, sqrt
from operator import itemgetter
from optparse import OptionParser
from daemonize import Daemonize
from subprocess import call
from os import system

class Bot(object):
	def __init__(self, config):
		# Constants:
		self.WOOD = '1'
		self.CLAY = '2'
		self.IRON = '3'
		self.CROP = '4'

		errorDelay = 10
		delay = 10

		self.config = config
		
		# Setting up cookies and proxy for urllib2:
		cookieHandler = HTTPCookieProcessor(CookieJar())
		proxyHandler = ProxyHandler(self.config.get()['login']['proxy'])
		opener = build_opener(cookieHandler, proxyHandler)
		install_opener(opener)

		config = self.config.get()

		self.server = config['login']['server']
		self.username = config['login']['username']
		self.password = config['login']['password']
		self.loggedIn = False

		self.login()

		while 1:
			try:
				build = int(self.config.get()['build']['enable'])
				if build:
					self.build()

				adventure = int(self.config.get()['adventures']['enable'])
				if adventure:
					self.adventure()

				sleep(delay)
			except KeyboardInterrupt:
				return
			except socket.timeout or URLError:
				log.warn('Internet connection error')
				continue
			except Exception, err:
				log.error(err)

				sleep(errorDelay)

	def login(self):
		self.loggedIn = False
		while not self.loggedIn:
			try:
				html = self.sendRequest(self.server)

				parser = BeautifulSoup(html)
				s1 = parser.find('button', {'name': 's1'})['value'].encode('utf-8')
				login = parser.find('input', {'name': 'login'})['value']

				data = {
					'name': self.username,
					'password': self.password,
					's1': s1,
					'w': '1366:768',
					'login': login
				}

				url = urljoin(self.server, 'dorf1.php')
				html = self.sendRequest(url, data)

				parser = BeautifulSoup(html)

				if parser.find('div', {'class': 'error LTR'}):
					log.warn('Cannot log in')
					raise self.UnableToLogIn

				log.info('Logged in successfully')

				self.loggedIn = True
				self.getInfo(html)
			except socket.timeout  or URLError:
				log.warn('Internet connection error')
				continue

	def build(self):
		config = self.config.get()
		buildingList = config['build']['buildingList']
		delay = config['build']['delay']

		for building in buildingList:
			sleep(delay)

			village = int(building['village'])
			fieldId = building['fieldId']
			skip = int(building['skip'])
			maxLvl = int(building['to'])

			villageId = config['info']['links'][village - 1]

			if fieldId == "res":
				wood = int(building['wood'])
				clay = int(building['clay'])
				iron = int(building['iron'])
				crop = int(building['crop'])

				upgradeDict = {
					self.WOOD: wood,
					self.CLAY: clay,
					self.IRON: iron,
					self.CROP: crop
				}

				params = urlencode({'newdid': villageId})
				url = urljoin(self.server, "dorf1.php?%s" %params)
				html = self.sendRequest(url)

				parser = BeautifulSoup(html)

				fields = parser.find_all('div', {'class': 'labelLayer'})
				fieldList = [field.find_parent('div')['class'] for field in fields]

				resources = self.getResources(html, upgradeDict)
				
				upgrade = min(resources, key = resources.get)

				fields = []
				for i, field in enumerate(fieldList, start = 1):
					underConstruction = field[3] == 'underConstruction'
					if underConstruction:
						log.info('Something is upgrading now in %d village. Waiting' %village)
						break

					gid = search('\d+', field[3]).group(0)

					if gid == upgrade:
						can = 1 if field[2] == 'good' else 0
						level = search('\d+', field[4]).group(0)

						fields.append({
							'id': str(i),
							'can': can, 
							'level': level
						})

				if underConstruction:
					if skip:
						continue
					break

				fields.sort(key = itemgetter('can'))
				fields.sort(key = itemgetter('level'))

				fieldId = fields[0]['id']

			log.info('Trying to upgrade id%s in %d village' %(fieldId, village))

			params = urlencode({
				'id': fieldId,
				'newdid': villageId
			})
			url = urljoin(self.server, 'build.php?%s' %params)
			html = self.sendRequest(url)

			if 'container active' in html: # Tabs in building
				log.debug('Switching to 1st tab')

				tab = findall('href="build.php\?(\w+)=\d+', html)[0]

				params = urlencode({
					'id': fieldId,
					'newdid': villageId,
					tab: '0'
				})
				url = urljoin(self.server, 'build.php?%s' %params)
				html = self.sendRequest(url)

			if 'gid0' in html: # Not built yet
				log.info('There is no building in id%s in %d village yet' %(fieldId, village))

				if int(building['build']):
					gid = building['gid']
					category = building['category']

					log.info('Trying to build %s in id%s in %d village' %(gid, fieldId, village))

					params = urlencode({
						'id': fieldId,
						'gid': gid,
						'newdid': villageId,
						'category': category
					})
					url = urljoin(self.server, 'build.php?%s' %params)
					html = self.sendRequest(url)

					c = search('a=%s&amp;id=%s&amp;c=(\w+)' %(gid, fieldId), html)
					if not c:
						log.info('Cannot build %s in id%s in %d village' %(gid, fieldId, village))
						if skip:
							continue
						break

					c = c.group(0)
					params = urlencode({
						'a': gid,
						'id': fieldId,
						'c': c,
						'newdid': villageId
					})
					url = urljoin(self.server, 'dorf2.php?%s' %params)
					html = self.sendRequest(url)

					log.info('Successfully built %s in id%s in %d village' %(gid, fieldId, village))

			parser = BeautifulSoup(html)

			lvl = parser.find('span', {'class': 'level'}).text
			currentLvl = int(findall('(\d+)', lvl)[0])
			upgradingNow = parser.find('tr', {'class': 'underConstruction'})

			if upgradingNow:
				currentLvl += 1

			if currentLvl >= maxLvl:
				buildingList.remove(building)

				log.debug('Building task ended (id%s in %d village to %d lvl)' %(fieldId, village, maxLvl))

				if not buildingList:
					log.debug('No more building tasks')
					enable = 0
				else:
					enable = 1
				
				self.config.set('build', {
					'enable': enable, 
					'delay': delay,
					'buildingList': buildingList
				})
				if skip:
					continue
				break

			buildLink = parser.find('button', {'class': 'green build'})

			if not buildLink:
				notEnoughRes = 'little_res' in html
				if notEnoughRes:
					if not skip:
						log.info('Not enough resources to upgrade id%s in %d village. Waiting' %(fieldId, village))
						break
					log.info('Not enough resources to upgrade id%s in %d village. Skipping to the next' %(fieldId, village))
					continue

				params = urlencode({'newdid': villageId})
				url = urljoin(self.server, 'dorf1.php?%s' %params)
				html = self.sendRequest(url)

				waitingParser = BeautifulSoup(html)
				somethingIsUpgrading = parser.find('div', {'class': 'finishNow'})
				if somethingIsUpgrading:
					log.info('Something is being upgraded now in %d village. Waiting' %village)
					if skip:
						continue
					break

				log.info('Cannot upgrade id%s in %d village. Waiting' %(fieldId, village))
				if skip:
					continue
				break

			c = findall('c=(\w+)', buildLink['onclick'])[0]

			params = urlencode({
				'c': c,
				'a': fieldId,
				'newdid': villageId
			})

			if int(fieldId) < 19:
				dorf = 'dorf1.php'
			else:
				dorf = 'dorf2.php'

			url = urljoin(self.server, '%s?%s' %(dorf, params))
			self.sendRequest(url)

			log.info('id%s in %d village successfully upgraded to %d' %(fieldId, village, currentLvl + 1))

	def getResources(self, html, res = {'1': 1, '2': 1, '3': 1, '4': 1}):
		resourcesNumber = 4
		parser = BeautifulSoup(html)

		for resource in res.keys():
			if res[resource]:
				res[resource] = int(parser.find('span', {'id': 'l%s' %resource}).text)
			else:
				del res[resource]

		return res

	def getInfo(self, html):
		villageLinks = findall('\?newdid=(\d+)', html)
		villageAmount = len(villageLinks)

		nation = findall('nation(\d)', html)[0]

		X = findall('coordinateX">\(&#x202d;&(#45;)*&*#x202d;(\d+)', html)
		Y = findall('coordinateY">&#x202d;&(#45;)*&*#x202d;(\d+)', html)

		ajaxToken = findall('ajaxToken\s*=\s*\'(\w+)\'', html)[0]

		x = []
		y = []
		
		for i in xrange(villageAmount):
			if '#45' in X[i][0]:
				x.append('-%s' %X[i][1])
			else:
				x.append(X[i][1])
			if '#45' in Y[i][0]:
				y.append('-%s' %Y[i][1])
			else:
				y.append(Y[i][1])

		self.config.set("info", {
			'villages': villageAmount,
			'links': villageLinks,
			'x': x,
			'y': y,
			'nation': nation,
			'ajaxToken': ajaxToken
		})

	def adventure(self):
		url = urljoin(self.server, 'dorf1.php')
		html = self.sendRequest(url)

		adventures = int(search('"boxId":"hero","disabled":false,"speechBubble":"(\d+)', html).group(1))

		if adventures:
			if 'heroStatus100' in html:
				log.info('New adventure')
			else:
				return

			url = urljoin(self.server, 'hero_adventure.php')
			html = self.sendRequest(url)

			kid = search('adventure(\d+)', html).group(1)

			params = urlencode({
				'from': 'list',
				'kid': kid,
			})

			url = urljoin(self.server, 'start_adventure.php?%s' %params)
			html = self.sendRequest(url)

			parser = BeautifulSoup(html)
			start = parser.find('button', {'id': 'start'})['value'].encode('utf-8')

			data = {
				'send': 1,
				'from': 'list',
				'kid': kid,
				'a': 1,
				'start': start
			}

			url = urljoin(self.server, 'start_adventure.php')
			html = self.sendRequest(url, data)

			if 'heroStatus50' in html:
				log.info('Adventure started successfully')
				return

			log.warn('Something went wrong while starting adventure')

	def sendRequest(self, url, data = {}):
		argData = data
		data = urlencode(argData)

		blocked = True
		while blocked:
			req = Request(url, data)
			resp = urlopen(req, timeout = 5)
			html = resp.read()
			
			log.debug(resp.geturl())

			blocked = 'FF0000' in html
			
			if blocked:
				log.warn('You are blocked')
				sleep(60)

		if self.loggedIn and not 'ajax.php' in url:
			if 'playerName' not in html:
				log.warn('Suddenly logged off')
				self.loggedIn = False

				reconnects = 0
				tryAgain = True
				while reconnects <= 5 and tryAgain:
					try:
						self.login()

						html = self.sendRequest(url, argData)

						tryAgain = False
					except self.UnableToLogIn:
						reconnects += 1

						log.error('Could not relogin %d time' %reconnects)

						sleep(errorDelay)

		return html

	class UnableToLogIn(Exception):
		pass
			

class Config(object):
	def __init__(self, filename):
		self.filename = filename
		self.lastModification = 0
		self.config = {}

		if not os.path.exists(self.filename):
			log.critical('No config file: %s' %self.filename)
			raise Exception('No config file: %s' %self.filename)

		self.lastModification = os.path.getmtime(self.filename)

		with open(self.filename, 'r') as f:
			self.config = json.load(f)

	def update(self):
		lastModification = os.path.getmtime(self.filename)
		if lastModification > self.lastModification:
			self.lastModification = lastModification
			with open(self.filename, 'r') as f:
				self.config = json.load(f)

	def get(self):
		self.update()
		return self.config

	def set(self, key, value):
		self.update()
		self.config[key] = value

		with open(self.filename, 'w') as f:
			json.dump(self.config, f, indent = 4)

def setUpLogger(logPath):
	global log

	log = logging.getLogger('bot')
	log.setLevel(logging.DEBUG)

	fileHandler = logging.FileHandler(logPath)

	fileHandler.setLevel(logging.DEBUG)

	fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

	log.addHandler(fileHandler)

	return fileHandler

class Daemon(object):
	def __init__(self, config):
		self.workingDirectory = os.path.dirname(os.path.abspath(__file__))
		self.config = config
		self.pidFile = '/tmp/bot_%s.pid' %(self.config.replace('.json', ''))

	def main(self):
		config = Config(os.path.join(self.workingDirectory, self.config))
		Bot(config)

	def start(self):
		fileHandler = setUpLogger(os.path.join(self.workingDirectory, 'debug.log'))

		keep_fds = [fileHandler.stream.fileno()]

		Daemonize(app = 'bot', pid = self.pidFile, action = self.main, keep_fds = keep_fds, verbose = True, logger = log).start()

	def stop(self):
		try:
			with open(self.pidFile, 'r') as f:
				pid = int(f.read())
		except OSError:
			print 'Error: Daemon is not running'

		system('kill -15 %d' %pid)

if __name__ == '__main__':
	parser = OptionParser(usage="usage: %prog config_filename start|stop")
	(options, args) = parser.parse_args()
	
	if len(args) == 2:
		config = args[0]

		daemon = Daemon(config)

		if 'start' == args[1]:
			daemon.start()
		elif 'stop' == args[1]:
			daemon.stop()
		else:
			parser.error("Unknown command: %s" %args[1])
		sys.exit(0)
	else:
		parser.error("Wrong number of arguments")

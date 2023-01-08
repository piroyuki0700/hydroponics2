#!/usr/bin/python3
#
# RaspberryPI操作モジュール
#

import RPi.GPIO as GPIO
import adafruit_dht
from board import *
import smbus
import time
import re
from decimal import *
from datetime import datetime
import logging
import traceback
import json
import threading

#AD/DAモジュール設定
address = 0x48
A0 = 0x40
A1 = 0x41
A2 = 0x42
A3 = 0x43

# GPIO.BCM番号
gpio_led = {'blue': 19, 'green': 26, 'yellow': 21, 'red': 20}

gpio_dht11 = D13
gpio_ds18 = 7
gpio_pump = 6
gpio_air = 5
gpio_subpump = 10
gpio_nightly = 4

gpio_float_upper = 24
gpio_float_lower = 23
gpio_float_sub = 18

gpio_trig = 12
gpio_echo = 16
MAX_DISTANCE = 220
VALID_DISTANCE_MIN = 3
VALID_DISTANCE_MAX = 30
WATER_LEVEL_MAX = 29
WATER_LEVEL_FULL = 20

SYSFILE_DS18B20 = '/sys/bus/w1/devices/28-01204c43b99b/w1_slave'
RETRY_TEMPHUMID_MAX = 5
RETRY_TEMPHUMID_DELAY = 1
RETRY_WATERTEMP_MAX = 5
RETRY_WATERTEMP_DELAY = 0.5
RETRY_DISTANCE_MAX = 10
RETRY_DISTANCE_DELAY = 0.5
RETRY_TDS_MAX = 10
RETRY_TDS_DELAY = 0.5

class CHydroRaspiController():
	logger = None
	event_subpump = None

	def __init__(self, logger):
		self.logger = logger
		self.logger.debug("called")
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		self.event_subpump = threading.Event()

	def __del__(self):
		self.logger.debug("called")
		GPIO.cleanup()
		if self.event_subpump != None:
			del self.event_subpump

	def switch_continuous(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_air, GPIO.OUT)
		GPIO.output(gpio_air, GPIO.HIGH if enable is True else GPIO.LOW)

	def switch_blinking(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_pump, GPIO.OUT)
		GPIO.output(gpio_pump, GPIO.HIGH if enable is True else GPIO.LOW)

	def measure_temp_humid(self):
		self.logger.debug("called")

		result = {'air_temp': None, 'humidity': None}
		for i in range(RETRY_TEMPHUMID_MAX):
			try:
				dht11 = adafruit_dht.DHT11(gpio_dht11, use_pulseio=False)
				temperature = dht11.temperature
				humidity = dht11.humidity
				result = {'air_temp': float(f"{temperature:.1f}"), 'humidity': float(f"{humidity:.1f}")}
				break
			except Exception as e:
				self.logger.error(e)
			time.sleep(RETRY_TEMPHUMID_DELAY)

		return result

	def measure_water_temp(self):
		self.logger.debug("called")
		GPIO.setup(gpio_ds18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		result = {'water_temp': None}
		for i in range(RETRY_WATERTEMP_MAX):
			try:
				with open(SYSFILE_DS18B20, mode='r') as f:
					striped = [line.strip() for line in f.readlines()]
					self.logger.debug(f"{striped}")
					f.close()
					if 'YES' in striped[0]:
						values = re.findall(r't=([0-9]+)', striped[1])
						water_temp = int(values[0]) / 1000
						result = {'water_temp': float(f"{water_temp:.1f}")}
						break
			except Exception as e:
				self.logger.error(e)
			time.sleep(RETRY_WATERTEMP_DELAY)

		return result

	def pulseIn(self, pin, level, timeOut):
		t0 = time.time()
		while(GPIO.input(pin) != level):
			if((time.time() - t0) > timeOut * 0.000001):
				return 0
		t0 = time.time()
		while(GPIO.input(pin) == level):
			if((time.time() - t0) > timeOut * 0.000001):
				return 0
		pulseTime = (time.time() - t0) * 1000000
		return pulseTime
	
	def getSonar(self):
		GPIO.setup(gpio_trig, GPIO.OUT)
		GPIO.setup(gpio_echo, GPIO.IN)
		GPIO.output(gpio_trig, GPIO.HIGH)
		time.sleep(0.00001)
		GPIO.output(gpio_trig, GPIO.LOW)
		pingTime = self.pulseIn(gpio_echo, GPIO.HIGH, MAX_DISTANCE * 60)
		distance = pingTime * 340.0 / 2.0 / 10000.0
		return distance

	def measure_water_level(self):
		self.logger.debug("called")

		measured = False
		for i in range(RETRY_DISTANCE_MAX):
			distance = self.getSonar()
			self.logger.debug(f"count:{i}: {distance}")
			if VALID_DISTANCE_MIN <= distance and distance <= VALID_DISTANCE_MAX:
				measured = True
				break
			time.sleep(RETRY_DISTANCE_DELAY)

		result = {'distance': None, 'water_level': None}
		if measured == True:
			# %を計算（0～に制限）
			water_level = int((WATER_LEVEL_MAX - distance) * 100 / WATER_LEVEL_FULL)
#			water_level = min(100, max(water_level, 0))
			water_level = max(water_level, 0)
			self.logger.debug(f"distance:{distance} water_level:{water_level}")
			if 0 < water_level:
				result = {'distance': float(f"{distance:.1f}"), 'water_level': water_level}

		return result

	def measure_tds(self, temperature):
		self.logger.debug("called")
		AREF = 5
		ADCRANGE = 256
		KVALUE = 1.0274
		bus = smbus.SMBus(1)
		bus.write_byte(address,A2)

		measured = False
		for i in range(RETRY_TDS_MAX):
			value = bus.read_byte(address)
			self.logger.debug(f"{i}: {value}")
			if 0 < value and value < 100:
				measured = True
				break
			time.sleep(RETRY_TDS_DELAY)

		result = {'voltage': None, 'tds_level': None}
		if measured == True:
			voltage = value * AREF / ADCRANGE
			ecValue = (133.42*voltage**3 - 255.86*voltage**2 + 857.39*voltage) * KVALUE
			if temperature == None:
				ecValue25 = ecValue
				self.logger.debug(f"ecValue={ecValue} (not adjust)")
			else:
				ecValue25 = ecValue / (1.0+0.02*(temperature-25.0))
				self.logger.debug(f"ecValue={ecValue}, ecValue25={ecValue25}")
			ecResult = ecValue25 / 1000
			result =  {'voltage': float(f"{voltage:.2f}"), 'tds_level': float(f"{ecResult:.2f}")}

		return result

	def measure_brightness(self):
		self.logger.debug("called")
		bus = smbus.SMBus(1)
		bus.write_byte(address,A0)
		value = bus.read_byte(address)
		time.sleep(0.1)
		value = bus.read_byte(address)	# 2回読まないとあまり変化しない
		bus.close()
		return {'brightness': 255 - value}

	# センサー値の取得（デバッグメニュー用）
	def measure_sensor(self, sensor_kind):
		self.logger.debug("called")
		if sensor_kind == "temp_humid":
			return self.measure_temp_humid()
		elif sensor_kind == "water_temp":
			return self.measure_water_temp()
		elif sensor_kind == "water_level":
			return self.measure_water_level()
		elif sensor_kind == "tds_level":
			result = self.measure_water_temp()
			return self.measure_tds(result['water_temp'])
		elif sensor_kind == "brightness":
			return self.measure_brightness()
		else:
			return None

	# 全センサー値の取得
	def measure_sensors(self):
		self.logger.debug("called")
		try:
			result = self.measure_temp_humid()
			result.update(self.measure_water_temp())
			result.update(self.measure_water_level())
			result.update(self.measure_tds(result['water_temp']))
			result.update(self.measure_brightness())
			return result
		except Exception as e:
#			self.logger.error(f"Exception {e}")
			self.logger.error(traceback.format_exc())
			return {}

	# LED ON/OFF
	def set_led(self, color, state):
		self.logger.debug(f"called. {color}={state}")
		output = GPIO.HIGH if state == "on" else GPIO.LOW
		GPIO.setup(gpio_led[color], GPIO.OUT)
		GPIO.output(gpio_led[color], output)
		return True

	# 状態表示LED更新
	def update_led(self, color):
		self.logger.debug(f"called. color={color}")
		for key in gpio_led:
			self.set_led(key, 'on' if color == key else 'off')
		return True

	# サブポンプ直接操作
	def subpump_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_subpump, GPIO.OUT)
		GPIO.output(gpio_subpump, GPIO.HIGH if enable is True else GPIO.LOW)
		return True

	# サブタンクの水の状態確認
	def subpump_available(self):
		self.logger.debug("called")
		GPIO.setup(gpio_float_sub, GPIO.IN)
		level = GPIO.input(gpio_float_sub)
		return level == GPIO.HIGH

	# サブタンクの水終了コールバック
	def subpump_empty(self):
		self.logger.warning("The sub tank is empty.")
		self.event_subpump.set()

	# サブタンクからの水補充
	def subpump_refill(self, min, max):
		self.logger.debug("called")
		GPIO.add_event_detect(gpio_float_sub, GPIO.FALLING, self.subpump_empty, 1000)

		start_time = datetime.now()
		self.logger.debug("start_time: " + start_time.strftime('%Y/%m/%d %H:%M:%S'))
		self.subpump_switch(True)

		ret = self.event_subpump.wait(max)
		if ret == True:
			time.sleep(min) # センサー感知から最短動作させて停止

		self.subpump_switch(False)
		end_time = datetime.now()

		past = int((end_time - start_time).total_seconds()) + 1
		self.event_subpump.clear()

		return {'past': past, 'empty': ret}


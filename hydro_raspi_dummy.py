#!/usr/bin/python3
#
# RaspberryPI操作モジュール
#

#import RPi.GPIO as GPIO
#import adafruit_dht
#from board import *
#import smbus
import time
#import re
from decimal import *
from datetime import datetime
import logging
import traceback
import json

##AD/DAモジュール設定
#address = 0x48
#A0 = 0x40
#A1 = 0x41
#A2 = 0x42
#A3 = 0x43
#
## GPIO.BCM番号
##gpio_led = [35,36,37,38]
#gpio_led = [19,16,26,20]
#gpio_dht11 = D18	# 12番のBCM GPIO番号
#gpio_ds18 = 4
#gpio_pump = 17

gpio_trig = 23
gpio_echo = 24
MAX_DISTANCE = 220
timeOut = MAX_DISTANCE*60
WATER_LEVEL_MAX = 29
WATER_LEVEL_FULL = 20

SYSFILE_DS18B20 = '/sys/bus/w1/devices/28-01204c43b99b/w1_slave'
RETRY_TDS_MAX = 5
RETRY_TDS_DELAY = 0.5
RETRY_DISTANCE_MAX = 30
RETRY_DISTANCE_DELAY = 0.5

gpio_subp_relay = 5
gpio_subp_level = 6

class CHydroRaspiController():
	logger = None
	subpump_status = False

	def __init__(self, logger):
		self.logger = logger
		self.logger.debug("called")

	def __del__(self):
		self.logger.debug("called")

	def switch_continuous(self, enable):
		self.logger.debug(f"called. enable={enable}")

	def switch_blinking(self, enable):
		self.logger.debug(f"called. enable={enable}")

	def measure_temp_humid(self):
		self.logger.debug("called")
		return {'air_temp': 25.5, 'humidity': 45.6}
#		return {'air_temp': None, 'humidity': None}

	def measure_water_temp(self):
		self.logger.debug("called")
		return {'water_temp': 23.4}
#		return {'water_temp': None}

	def measure_water_level(self):
		self.logger.debug("called")
		distance = 27

		# %を計算（0～100に制限）
		water_level = int((WATER_LEVEL_MAX - distance) * 100 / WATER_LEVEL_FULL)
		water_level = min(100, max(water_level, 0))
		return {'distance': float(f"{distance:.1f}"), 'water_level': water_level}

	def measure_tds(self, temperature):
		self.logger.debug("called")
		AREF = 5
		ADCRANGE = 256
		KVALUE = 1.0274

		value = 50

		if temperature is None:
			temperature = 25.0

		voltage = value * AREF / ADCRANGE
		ecValue = (133.42*voltage**3 - 255.86*voltage**2 + 857.39*voltage) * KVALUE
		ecValue25 = ecValue / (1.0+0.02*(temperature-25.0))
		self.logger.debug(f"ecValue={ecValue}, ecValue25={ecValue25}")
		ecResult = ecValue25 / 1000
		return {'voltage': float(f"{voltage:.2f}"), 'tds_level': float(f"{ecResult:.2f}")}
	
	def measure_brightness(self):
		self.logger.debug("called")
		return {'brightness': 30}

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

	# タンクの水チェック
	def check_float_upper(self):
		self.logger.debug("called")
		return False

	def check_float_lower(self):
		self.logger.debug("called")
		return True

	# LED ON/OFF
	def set_led(self, color, state):
		self.logger.debug(f"called. {color}={state}")
		return True

	# 状態表示LED更新
	def update_led(self, color):
		self.logger.debug(f"called. color={color}")
		return True

	# サブポンプ動作
	def subpump_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		self.subpump_status = enable
		return True

	# サブタンクの水の状態確認
	def subpump_available(self):
		self.logger.debug("called")
		return True

	# サブタンクの水終了コールバック
	def subpump_callback(self):
		self.logger.debug("called")

	# サブタンクからの水補充
	def subpump_refill(self, min, max):
		time.sleep(10)
		return {'past': 10, 'empty': True}

	# 夜間スイッチ
	def nightly_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")

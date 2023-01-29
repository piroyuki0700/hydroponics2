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
import traceback
import threading

#AD/DAモジュール設定
adda_address = 0x48
adda_AIN0 = 0x40
adda_AIN1 = 0x41
adda_AIN2 = 0x42
adda_AIN3 = 0x43

# GPIO.BCM番号
gpio_led = {'blue': 19, 'green': 26, 'yellow': 21, 'red': 20}

gpio_dht11 = D13
gpio_ds18 = 7 # 1wire device. need to write the gpio setting in /boot/config.txt to use non-default gpio number
gpio_pump = 6
gpio_air = 5
gpio_subpump = 10
gpio_nightly = 4

gpio_float_upper = 24
gpio_float_lower = 23
gpio_float_sub = 18

gpio_trig = 12
gpio_echo = 16

# パルス検出タイムアウト
SONAR_TIMEOUT = (10 / 1000) # 10ms
# 水面までの距離の有効範囲
VALID_DISTANCE_MIN = 3
VALID_DISTANCE_MAX = 30
# センサーから底までの距離
SENSOR_DISTANCE = 29
# 満水時の水位
WATER_LEVEL_FULL = 20

# 水温計のデバイスファイル
SYSFILE_DS18B20 = '/sys/bus/w1/devices/28-01204c43b99b/w1_slave'
# 各センサーのリトライ回数とディレイ
RETRY_TEMPHUMID_MAX = 3
RETRY_TEMPHUMID_DELAY = 1
RETRY_WATERTEMP_MAX = 3
RETRY_WATERTEMP_DELAY = 0.5
RETRY_DISTANCE_MAX = 5
RETRY_DISTANCE_DELAY = 0.5
RETRY_TDS_MAX = 5
RETRY_TDS_DELAY = 0.5

class CHydroRaspiController():
	logger = None
	event_subpump = None
	subpump_working = False

	def __init__(self, logger):
		self.logger = logger
		self.logger.debug("called")
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		GPIO.setup(gpio_ds18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(gpio_float_upper, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
		GPIO.setup(gpio_float_lower, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
		GPIO.setup(gpio_float_sub, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
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
			if((time.time() - t0) > timeOut):
				return 0
		t0 = time.time()
		while(GPIO.input(pin) == level):
			if((time.time() - t0) > timeOut):
				return 0
		pulseTime = (time.time() - t0) * 1000000
		return pulseTime
	
	def getSonar(self):
		GPIO.setup(gpio_trig, GPIO.OUT)
		GPIO.setup(gpio_echo, GPIO.IN)
		GPIO.output(gpio_trig, GPIO.HIGH)
		time.sleep(0.00001)
		GPIO.output(gpio_trig, GPIO.LOW)
		pingTime = self.pulseIn(gpio_echo, GPIO.HIGH, SONAR_TIMEOUT)
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
			water_level = int((SENSOR_DISTANCE - distance) * 100 / WATER_LEVEL_FULL)
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
		bus.write_byte(adda_address, adda_AIN2)

		measured = False
		for i in range(RETRY_TDS_MAX):
			value = bus.read_byte(adda_address)
			self.logger.debug(f"{i}: {value}")
			if 0 < value and value < 100:
				measured = True
				break
			time.sleep(RETRY_TDS_DELAY)

		result = {'voltage': None, 'tds_level': None}
		if measured == True:
			voltage = value * AREF / ADCRANGE
			ecValue = (133.42*voltage**3 - 255.86*voltage**2 + 857.39*voltage) * KVALUE
			if temperature is None:
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
		bus.write_byte(adda_address, adda_AIN0)
		value = bus.read_byte(adda_address)
		time.sleep(0.1)
		value = bus.read_byte(adda_address)	# 2回読まないとあまり変化しない
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

	# タンクの水チェック
	def check_float_upper(self):
		self.logger.debug("called")
		float_sw = GPIO.input(gpio_float_upper)
		return float_sw == GPIO.HIGH

	def check_float_lower(self):
		self.logger.debug("called")
		float_sw = GPIO.input(gpio_float_sub)
		return float_sw == GPIO.HIGH

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
		self.subpump_working = enable
		GPIO.setup(gpio_subpump, GPIO.OUT)
		GPIO.output(gpio_subpump, GPIO.HIGH if enable is True else GPIO.LOW)
		return True

	# サブタンクの水の状態確認
	def subpump_available(self):
		self.logger.debug("called")
		float_sw = GPIO.input(gpio_float_sub)
		return float_sw == GPIO.LOW

	# サブタンクの水終了コールバック
	def subpump_callback(self):
		self.logger.warning("cancel subpump")
		self.event_subpump.set()

	# サブタンクからの水補充
	def subpump_refill(self, min, max):
		self.logger.debug("called")
		self.event_subpump.clear()

		# サブタンクの水がなくなった場合
		GPIO.add_event_detect(gpio_float_sub, GPIO.RISING, self.subpump_callback, 1000)
		# メインタンクが満タンになった場合
		GPIO.add_event_detect(gpio_float_upper, GPIO.RISING, self.subpump_callback, 1000)

		start_time = datetime.now()
		self.logger.debug("start_time: " + start_time.strftime('%Y/%m/%d %H:%M:%S'))
		self.subpump_switch(True)

		ret = self.event_subpump.wait(max)
		if ret == True:
			time.sleep(min) # センサー感知から最短動作させて停止

		self.subpump_switch(False)
		end_time = datetime.now()

		past = int((end_time - start_time).total_seconds()) + 1
		GPIO.remove_event_detect(gpio_float_sub)
		GPIO.remove_event_detect(gpio_float_upper)
		self.event_subpump.clear()

		empty = not self.subpump_available()
		return {'past': past, 'empty': empty}

	# 夜間スイッチ
	def nightly_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_nightly, GPIO.OUT)
		GPIO.output(gpio_nightly, GPIO.HIGH if enable is True else GPIO.LOW)
		return True

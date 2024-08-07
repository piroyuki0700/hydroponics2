#!/usr/bin/python3
#
# RaspberryPI操作モジュール
#

import RPi.GPIO as GPIO
import neopixel
import adafruit_dht
import board
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

# 水温計のデバイスファイル
SYSFILE_DS18B20 = '/sys/bus/w1/devices/28-01204c43b99b/w1_slave'

# GPIO.BCM番号
gpio_led = board.D18
gpio_dht11 = board.D5
gpio_ds18 = 11 # 1wire device. need to write the gpio setting in /boot/config.txt to use non-default gpio number
gpio_fan = 21
# USB
gpio_air = 16
gpio_pump = 19
gpio_usb = 20
gpio_subpump = 26
# SSR
gpio_circulator = 6
gpio_nightly = 13
# switch
gpio_float_upper = 27
gpio_float_lower = 17
gpio_float_sub = 15
# ultra sonic
gpio_trig = 14
gpio_echo = 4

# パルス検出タイムアウト
SONAR_TIMEOUT = (30 / 1000) # ms
# 水面までの距離の有効範囲
VALID_DISTANCE_MIN = 3
VALID_DISTANCE_MAX = 32
# センサーから底までの距離
SENSOR_DISTANCE = 29
# 満水時の水位
WATER_LEVEL_FULL = 20

# 水の補充のチェック間隔
WATER_REFILL_INTERVAL = 3

# 各センサーのリトライ回数とディレイ
RETRY_TEMPHUMID_MAX = 5
RETRY_TEMPHUMID_DELAY = 0.8
RETRY_WATERTEMP_MAX = 3
RETRY_WATERTEMP_DELAY = 0.5
RETRY_DISTANCE_MAX = 6
RETRY_DISTANCE_DELAY = 0.5
RETRY_TDS_MAX = 6
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
			water_level = 0
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
			water_level = max(water_level, 0)
			if 0 <= water_level:
				result = {'distance': float(f"{distance:.1f}"), 'water_level': water_level}

		self.logger.debug(f"distance:{distance} water_level:{water_level}")
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
			time.sleep(0.1)
			value = bus.read_byte(adda_address)     # 2回読まないとあまり変化しない
			self.logger.debug(f"{i}: {value}")
			if 10 <= value and value < 100:
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
		return float_sw == GPIO.LOW

	def check_float_lower(self):
		self.logger.debug("called")
		float_sw = GPIO.input(gpio_float_lower)
		return float_sw == GPIO.LOW

	# 状態表示LED更新
	def update_led(self, color):
		self.logger.debug(f"called. color={color}")
		pixels = neopixel.NeoPixel(gpio_led, 1)
		if color == 'blue':
			pixels[0] = (0, 0, 50)
		elif color == 'green' or color == 'success':
			pixels[0] = (50, 0, 0)
		elif color == 'yellow' or color == 'warning':
			pixels[0] = (32, 32, 0)
		elif color == 'red' or color == 'danger':
			pixels[0] = (0, 50, 0)
		elif color == 'cyan':
			pixels[0] = (32, 0, 32)
		elif color == 'magenta':
			pixels[0] = (0, 32, 32)
		elif color == 'white':
			pixels[0] = (20, 20, 20)
		else:
			pixels[0] = (0, 0, 0)
		return True

	# サブポンプ直接操作
	def subpump_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		self.subpump_working = enable
		GPIO.setup(gpio_subpump, GPIO.OUT)
#		enable = False # デバッグ用。実際のサブポンプ動作なし
		GPIO.output(gpio_subpump, GPIO.HIGH if enable is True else GPIO.LOW)
		return True

	# サブタンクの水の状態確認
	def subpump_available(self):
		self.logger.debug("called")
		float_sw = GPIO.input(gpio_float_sub)
		return float_sw == GPIO.LOW

	# サブタンクからの水補充中断
	def subpump_cancel(self):
		self.logger.warning(f"cancel subpump (working={self.subpump_working})")
		ret = False
		if self.subpump_working is True:
			self.event_subpump.set()
			ret = True
		return ret
		
	# サブタンクからの水補充
	def subpump_exec(self, max, check_sub=True, lap_callback=None):
		self.logger.debug("called")
		self.event_subpump.clear()

		start_time = datetime.now()
		self.logger.debug("start_time: " + start_time.strftime('%Y/%m/%d %H:%M:%S'))
		self.subpump_switch(True)

		remain = max
		current = 0
		while 0 < remain:
			if WATER_REFILL_INTERVAL < remain:
				current = WATER_REFILL_INTERVAL
			else:
				current = remain
			remain -= current

			ret = self.event_subpump.wait(current)
			if ret is True:
				self.logger.debug("subpump canceled.")
				break # キャンセルされたとき
			if check_sub is True and self.subpump_available() is False:
				self.logger.debug("subpump stop (not available)")
				break # サブタンクの水がなくなったとき
			if self.check_float_upper() is True:
				self.logger.debug("subpump stop (water full)")
				break # タンクが満タンになったとき

			if remain != 0 and lap_callback is not None:
				lap_callback()

		self.subpump_switch(False)
		self.event_subpump.clear()

		end_time = datetime.now()
		past = int((end_time - start_time).total_seconds())
		if past == 0:
			past = past + 1

		empty = not self.subpump_available()
		return {'past': past, 'empty': empty}

	# 換気扇スイッチ
	def circulator_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_circulator, GPIO.OUT)
		GPIO.output(gpio_circulator, GPIO.HIGH if enable is True else GPIO.LOW)
		return True

	# 夜間スイッチ
	def nightly_switch(self, enable):
		self.logger.debug(f"called. enable={enable}")
		GPIO.setup(gpio_nightly, GPIO.OUT)
		GPIO.output(gpio_nightly, GPIO.HIGH if enable is True else GPIO.LOW)
		return True


#!/usr/bin/python3
#
# websocketサーバーメインモジュール
#
import asyncio
from concurrent.futures import ThreadPoolExecutor
import websockets
import threading
from datetime import datetime
from datetime import timedelta
import json
import tweepy
import requests
import subprocess
import os
import shutil
import logging
import logging.handlers
import sys
import signal

from hydro_raspi import CHydroRaspiController
#from hydro_raspi_dummy import CHydroRaspiController
from hydro_db_manage import CHydroDatabaseManager

MINUTE_START = 0
MINUTE_STOP = 50
MINUTE_REFILL = 55

DEFAULT_ONTIME = 7 * 60
DEFAULT_OFFTIME = 8 * 60

SUBPUMP_MANUAL_SECONDS = 60

SAVE_PICTURE_DIR = 'picture'
TMP_PICTURE_DIR = 'tmp_picture'

REFILL_TRIGGER_NONE = 0
REFILL_TRIGGER_SWITCH = 1
REFILL_TRIGGER_LEVEL = 2

SENSOR_ERROR_COUNT_LIMIT = 10

RETRY_CAMERA_MAX = 3
RETRY_CAMERA_DELAY = 3

class CHydroSwitcher():
	logger = None
	main_ctl = None
	raspi_ctl = None
	running = False
	th = None
	ontime = DEFAULT_ONTIME
	offtime = DEFAULT_OFFTIME
	event = None

	def __init__(self, logger, main_ctl, raspi_ctl):
		self.logger = logger
		self.logger.debug("called")
		self.main_ctl = main_ctl
		self.raspi_ctl = raspi_ctl
		self.event = threading.Event()

	def __del__(self):
		self.logger.debug("called")
		del self.event

	def main(self):
		self.logger.info(f"switcher loop start with ontime={self.ontime}, offtime={self.offtime}")
		self.raspi_ctl.switch_continuous(True)
		while self.running:
			# on
			self.main_ctl.pump_auto_cycle(True, self.ontime)
			self.raspi_ctl.switch_blinking(True)
			self.event.wait(self.ontime)
			# off
			self.main_ctl.pump_auto_cycle(False, self.offtime)
			self.raspi_ctl.switch_blinking(False)
			self.event.wait(self.offtime)
		self.raspi_ctl.switch_continuous(False)
		self.logger.info("switcher loop end")

	def start(self):
		self.logger.debug("called")
		if self.running:
			self.logger.warning("already started")
		else:
			self.running = True
			self.event.clear()
			self.th = threading.Thread(target=self.main, name="switcher")
			self.th.start()

	def stop(self):
		self.logger.debug("called")
		if self.running:
			self.running = False
			self.event.set()
			self.th.join()
			self.main_ctl.pump_auto_stop(None)

	def set_time(self, ontime, offtime):
		self.logger.info(f"change ontime={ontime}, offtime={offtime}")
		if ontime == 0:
			self.logger.warning("ontime is 0. not changed.")
		else:
			self.ontime = ontime

		if offtime == 0:
			self.logger.warning("offtime is 0. not changed.")
		else:
			self.offtime = offtime

class CHydroMainController():
	logger =None
	raspi_ctl = None
	db_manage = None
	websocketd = None
	switcher = None
	manual_timer = None
	schedule_timer = None
	executor_camera = None
	executor_report = None
	executor_subpump = None
	future_camera = None
	future_report = None
	future_subpump = None
	command_table = None
	prev_level = 100

	# keep latest schedule setting here
	schedule = None

	def __init__(self, logger):
		self.logger = logger
		self.logger.debug("called")
		self.raspi_ctl = CHydroRaspiController(self.logger)
		self.db_manage = CHydroDatabaseManager(self.logger)
		self.websocketd = CHydroWebsocketd(logger, self)
		self.switcher = CHydroSwitcher(self.logger, self, self.raspi_ctl)

		self.executor_camera = ThreadPoolExecutor(1, "camera")
		self.executor_report = ThreadPoolExecutor(1, "report")
		self.executor_subpump = ThreadPoolExecutor(1, "subpump")

		self.command_table = {
			'post_basic'       : self.post_basic,
			'post_schedule'    : self.post_schedule,
			'post_sensor_limit': self.post_sensor_limit,
			'tmp_report'       : self.tmp_report,
			'tmp_picture'      : self.tmp_picture,
			'save_picture'     : self.save_picture,
			'delete_picture'   : self.delete_picture,
			'set_led'          : self.set_led,
			'measure_sensor'   : self.measure_sensor,
			'pump_auto_start'  : self.pump_auto_start,
			'pump_auto_stop'   : self.pump_auto_stop,
			'pump_manual_start': self.pump_manual_start,
			'pump_manual_stop' : self.pump_manual_stop,
			'subpump_update'   : self.subpump_update,
			'subpump_refill'   : self.subpump_refill,
			'subpump_start'    : self.subpump_start,
			'subpump_stop'     : self.subpump_stop,
			'make_report'      : self.make_report,
			'test_tweet'       : self.test_tweet,
			'test_line'        : self.test_line,
			'test_ssr1'        : self.test_ssr1,
			'test_ssr2'        : self.test_ssr2,
			'debug_time_span'  : self.debug_time_span,
			'debug_echo'       : self.debug_echo,
		}

	def __del__(self):
		self.logger.debug("called")
		if self.future_camera != None:
			self.future_camera.result()
		if self.future_report != None:
			self.future_report.result()
		if self.future_subpump != None:
			self.future_subpump.result()

		if self.executor_camera != None:
			self.executor_camera.shutdown(wait=False)
			del self.executor_camera
		if self.executor_report != None:
			self.executor_report.shutdown(wait=False)
			del self.executor_report
		if self.executor_subpump != None:
			self.executor_subpump.shutdown(wait=False)
			del self.executor_subpump

		del self.websocketd
		del self.db_manage
		del self.raspi_ctl

	def start(self):
		self.db_manage.set_uptime()
		self.schedule = self.db_manage.get_schedule()
		self.scheduler_start()

	def scheduler_start(self):
		self.logger.info("called ------------------------------")

		if not int(self.schedule['schedule_active']):
			self.logger.info("schedule is inactive")
			self.raspi_ctl.update_led('none')
			return

		now = datetime.now()
		next_minute = now.minute
		(activate, ontime, offtime) = self.check_time_span(now)

		if activate == True:
			status = {}
			report = self.db_manage.get_latest_report()
			if len(report):
				status = self.evaluate(report)
				self.raspi_ctl.update_led(status['total_status'])
			else:
				self.raspi_ctl.update_led('white')

			if now.minute < MINUTE_START:
				self.logger.info("next start")
				next_minute = MINUTE_START
			elif now.minute < MINUTE_STOP:
				self.logger.info("next stop")
				self.switcher.set_time(ontime * 60, offtime * 60)
				self.switcher.start()
				if 'air_temp_status' in status:
					self.set_circulator(status['air_temp_status'])
				next_minute = MINUTE_STOP
			elif now.minute < MINUTE_REFILL:
				self.logger.info("next refill")
				self.switcher.stop()
				next_minute = MINUTE_REFILL
			else:
				self.logger.info("next start")
				next_minute = MINUTE_START

		else:
			self.switcher.stop()
			next_minute = MINUTE_START
			self.raspi_ctl.update_led('blue')

		self.set_next_timer(next_minute)

	def make_report(self, request=None):
		now = datetime.now()
		(activate, ontime, offtime) = self.check_time_span(now)
		self.execute_schedule(now, ontime, offtime)

	def scheduler_callback(self):
		try:
			self.scheduler_main()
		except Exception as e:
			self.logger.error(f"Unknown exception: {e}")
			self.set_next_timer(MINUTE_START)

	def scheduler_main(self):
		self.logger.debug("called ------------------------------")
		now = datetime.now()
		next_minute = now.minute
		(activate, ontime, offtime) = self.check_time_span(now)

		if activate == True:
			if now.minute == MINUTE_START:
				self.trigger_start(now, activate, ontime, offtime)
				next_minute = MINUTE_STOP
			elif now.minute == MINUTE_STOP:
				self.trigger_stop()
				next_minute = MINUTE_REFILL
			elif now.minute == MINUTE_REFILL:
				self.subpump_refill()
				next_minute = MINUTE_START
			else:
				self.logger.error(f"timer might expire at the wrong time. {now.hour}:{now.minute}:{now.second}")
				self.trigger_stop()
				next_minute = MINUTE_START
		else:
			inactive_string = 'inactive'
			if now.minute == MINUTE_START:
				self.trigger_start(now, activate, ontime, offtime)
			else:
				self.logger.error(f"timer might expire at the wrong time.")
				inactive_string = 'recovery'
				self.trigger_stop()

			next_minute = MINUTE_START
			data = {'command': 'inactive_color', 'activate': False, 'inactive_string': inactive_string}
			self.websocketd.broadcast(data)

		self.set_next_timer(next_minute)

	def set_next_timer(self, next_minute):
		now = datetime.now()
		next = now.replace(minute = next_minute, second = 0, microsecond = 0)
		if next_minute == MINUTE_START and MINUTE_START <= now.minute:
			next += timedelta(hours = 1)

		diff = next - now
		timestr = next.strftime('%Y/%m/%d %H:%M:%S')
		self.logger.info(f"next timer {diff.total_seconds()} to {timestr}")
		self.schedule_timer = threading.Timer(diff.total_seconds(), self.scheduler_callback)
		self.schedule_timer.start()

	def check_time_span(self, now):
		activate = True
		ontime = DEFAULT_ONTIME
		offtime = DEFAULT_OFFTIME

		if now.hour < self.schedule['time_morning'] or self.schedule['time_night'] <= now.hour:
			time_span = 'night'
			activate = False
			if int(self.schedule['nightly_active']):
				self.raspi_ctl.nightly_switch(True)
		else:
			self.raspi_ctl.nightly_switch(False)
			if self.schedule['time_evening'] <= now.hour:
				time_span = 'evening'
			elif self.schedule['time_noon'] <= now.hour:
				time_span = 'noon'
			else:
				time_span = 'morning'

			ontime = self.schedule[f'{time_span}_on']
			offtime = self.schedule[f'{time_span}_off']

		self.logger.info(f"hour = {now.hour}. it is {time_span} now.")
		return (activate, ontime, offtime)

	def stop(self):
		if self.manual_timer != None:
			self.manual_timer.cancel()
			del self.manual_timer
			self.manual_timer = None

		self.subpump_stop()
		self.scheduler_stop()
		self.raspi_ctl.update_led('none')

	def scheduler_stop(self):
		self.logger.info("called")
		self.switcher.stop()
		self.raspi_ctl.nightly_switch(False)
		self.raspi_ctl.circulator_switch(False)
		if self.schedule_timer != None:
			self.schedule_timer.cancel()
			del self.schedule_timer
			self.schedule_timer = None

	def run_server(self):
		asyncio.run(self.websocketd.websocket_server())

	def get_initial_data(self):
		self.logger.debug("called")
		data = {'command': 'initial_data'}
		data.update(self.db_manage.get_basic())
		data.update(self.db_manage.get_schedule())
		data.update(self.db_manage.get_sensor_limit())
		data.update(self.db_manage.get_pump_status())
		data.update(self.db_manage.get_latest_picture(SAVE_PICTURE_DIR))
		data.update(self.db_manage.get_latest_refill_record())
		report = self.db_manage.get_latest_report()
		if len(report):
			status = self.evaluate(report)
			data.update(report)
			data.update(status)
		data.update(self.subpump_status())

		now = datetime.now()
		(activate, ontime, offtime) = self.check_time_span(now)
		data['activate'] = activate
		if activate is False:
			data['inactive_string'] = 'inactive'
		return data

	def handle_request(self, request):
		command = request['command']
		self.logger.info(f"handle_request {command}")
		func = self.command_table[command]
		if func is None:
			message = f"funknown command [{command}] received."
			self.logger.error(message)
			response = self.make_result(False, message)
		else:
			response = func(request)
		return response

	def post_basic(self, request):
		self.logger.info(f"{request}")
		ret = self.db_manage.set_basic(request)
		if ret == True:
			data = self.db_manage.get_basic()
			data['command'] = 'setting_basic'
			self.websocketd.broadcast(data)
		return self.make_result(ret, "update basic setting")

	def post_schedule(self, request):
		ret = self.db_manage.set_schedule(request)
		if ret == True:
			data = self.db_manage.get_schedule()
			data['command'] = 'setting_schedule'
			self.websocketd.broadcast(data)
			self.schedule = data
			self.scheduler_stop()
			self.scheduler_start()
		return self.make_result(ret, "update schedule setting" , True)

	def post_sensor_limit(self, request):
		ret = self.db_manage.set_sensor_limit(request)
		if ret == True:
			data = self.db_manage.get_sensor_limit()
			data['command'] = 'setting_sensor_limit'
			self.websocketd.broadcast(data)
		return self.make_result(ret, "update sensor limit setting" , True)

	def trigger_start(self, now, activate, ontime, offtime):
		self.logger.debug("called")

		if int(self.schedule['schedule_active']):
			if activate:
				# in the schedule time
				self.execute_schedule(now, ontime, offtime)

			else:
				# out of the schedule time
				time_list = (self.schedule['time_spot1'],
					self.schedule['time_spot2'], self.schedule['time_spot3'])
				if now.hour in time_list:
					self.pump_manual_start({'seconds': self.schedule['spot_on'] * 60})

				self.raspi_ctl.update_led('blue')
		else:
			# inactive. nothing to do.
			self.raspi_ctl.update_led('none')

	def execute_schedule(self, now, ontime, offtime):
		self.logger.debug("called")
		camera = False
		result_camera = {}

		# make a report on another thread.
		self.future_report = self.executor_report.submit(self.report_main)

		# also take picture on another thread.
		time_list = (self.schedule['camera1'], self.schedule['camera2'],
			self.schedule['camera3'], self.schedule['camera4'], self.schedule['camera5'])
		if now.hour in time_list:
			camera = True
			self.future_camera = self.executor_camera.submit(self.camera_main, True)

		# wait until a report is created.
		report = self.future_report.result()
		self.logger.debug("executor_report completed.")
		report['report_time'] = now.strftime('%Y/%m/%d %H:%M:%S')

		# start cycle operation after a report is created.
		self.switcher.set_time(ontime * 60, offtime * 60)
		self.switcher.start()

		# wait until a picture is taken.
		if camera == True:
			result_camera = self.future_camera.result()
			if result_camera['picture_result'] == True:
				self.logger.debug("executor_camera completed.")
				# save the picture in db
				report['picture_no'] = self.db_manage.insert_picture(
					{'filename': result_camera['picture_name'], 'taken': result_camera['picture_taken']})
			else:
				self.logger.error("executor_camera failed.")

		# save the report in db
		report_no = self.db_manage.insert_report(report)
		self.logger.info(f"report No.{report_no} created.")

		self.logger.info(json.dumps(report))
		symbol = {'success': '〇', 'warning': '△', 'danger': '×'}
		message = "【自動送信】"
		if 'air_temp' in report:
			message += f"気温 {report['air_temp']}℃({symbol[report['air_temp_status']]})、"
			self.set_circulator(report['air_temp_status'])
		else:
			message += "気温 －、"
		if 'humidity' in report:
			message += f"湿度 {report['humidity']}％({symbol[report['humidity_status']]})、"
		else:
			message += "湿度 －、"
		if 'water_temp' in report:
			message += f"水温 {report['water_temp']}℃({symbol[report['water_temp_status']]})、"
		else:
			message += "水温 －、"
		if 'water_level' in report:
			message += f"水位 {report['water_level']}％ {report['distance']}cm ({symbol[report['water_level_status']]})、"
		else:
			message += "水位 －、"
			self.sensor_error('water_level')
		if 'tds_level' in report:
			message += f"濃度 EC{report['tds_level']}({symbol[report['tds_level_status']]})、"
		else:
			message += "濃度 －、"
		if 'brightness' in report:
			message += f"明るさ {report['brightness']}"
		else:
			message += "明るさ －"

		self.logger.debug(message)

		# select led color from total status
		self.raspi_ctl.update_led(report['total_status'])

		# tweet when it is a report time.
		if int(self.schedule['notify_active']) and self.schedule['notify_time'] == now.hour:
			self.tweet(message, result_camera['picture_path'] if camera == True else None)

		# line if any status is in danger.
		if int(self.schedule['emergency_active']) and report['total_status'] == 'danger':
			picture_path = None
			# take a picture now if not.
			if camera == True:
				if result_camera['picture_result'] == True:
					picture_path = result_camera['picture_path']
			else:
				self.future_camera = self.executor_camera.submit(self.camera_main)
				result_camera = self.future_camera.result()
				if result_camera['tmp_picture_result'] == True:
					picture_path = result_camera['tmp_picture_path']

			# send notification to the line account.
			self.line_notify(f"## 危険 ##\n{message}", picture_path)

		self.websocketd.broadcast(report)
		if 'water_level' in report:
			self.prev_level = report['water_level']

	def set_circulator(self, status):
		if status == 'danger' or status == 'warning':
			if int(self.schedule['circulator_active']):
				self.raspi_ctl.circulator_switch(True)

	def sensor_error(self, sensor):
		over_limit = self.db_manage.countup_sensor_error(sensor, SENSOR_ERROR_COUNT_LIMIT)
		if over_limit:
			self.line_notify(f"{sensor}センサー故障？{SENSOR_ERROR_COUNT_LIMIT}回連続計測失敗")

	def trigger_stop(self):
		self.logger.debug("called")
		self.switcher.stop()

	def subpump_refill(self, request=None):
		self.logger.debug("called")
		if self.schedule['refill_trigger'] == REFILL_TRIGGER_SWITCH:
			self.subpump_trigger_switch(request)
		elif self.schedule['refill_trigger'] == REFILL_TRIGGER_LEVEL:
			self.subpump_trigger_level()
		else:
			return self.make_result(False, "refill is disabled.")

	def tmp_report(self, request):
		loop = asyncio.get_running_loop()
		self.future_report = loop.run_in_executor(self.executor_report, self.report_main)
		return self.future_report

	def report_main(self):
		self.logger.debug("called")
		report = self.raspi_ctl.measure_sensors()
		if len(report):
			status = self.evaluate(report)
			report.update(status)
		report['command'] = 'report'
		return report

	def evaluate(self, report):
		self.logger.debug("called")
		status = {}
		danger = False
		warning = False
		success = False

		if report['brightness'] is not None:
			status['brightness_status'] = 'success'
		if report['distance'] is None:
			del report['distance']
		limit = self.db_manage.get_sensor_limit()
		items = ['air_temp', 'humidity', 'water_temp', 'water_level', 'tds_level']
		for item in items:
			if report[item] is None:
				del report[item]
				continue
			success = True

			vlow = f"{item}_vlow"
			if (vlow in limit):
				if (report[item] < limit[vlow]):
					status[f"{item}_status"] = 'danger'
					danger = True
					continue
			low = f"{item}_low"
			if (low in limit):
				if (report[item] < limit[low]):
					status[f"{item}_status"] = 'warning'
					warning = True
					continue
			vhigh = f"{item}_vhigh"
			if (vhigh in limit):
				if (report[item] > limit[vhigh]):
					status[f"{item}_status"] = 'danger'
					danger = True
					continue
			high = f"{item}_high"
			if (high in limit):
				if (report[item] > limit[high]):
					status[f"{item}_status"] = 'warning'
					warning = True
					continue
			status[f"{item}_status"] = 'success'

		if danger is True:
			status['total_status'] = 'danger'
		elif warning is True:
			status['total_status'] = 'warning'
		elif success is True:
			status['total_status'] = 'success'
		else:
			status['total_status'] = 'none'
		return status

	def tmp_picture(self, request):
		loop = asyncio.get_running_loop()
		self.future_camera = loop.run_in_executor(self.executor_camera, self.camera_main)
		return self.future_camera

	def camera_main(self, normal=False):
		self.logger.debug("called")
		if normal:
			result = self.exec_fswebcam(SAVE_PICTURE_DIR)
			self.websocketd.broadcast(result)
		else:
			result = self.exec_fswebcam(TMP_PICTURE_DIR)
		return result

	def exec_fswebcam(self, key):
		now = datetime.now()
		nowstr = now.strftime('%Y%m%d_%H%M%S')
		name = f"picture_{nowstr}.jpg"
		path = f"{key}/{name}"
		cmd = f'fswebcam -r 1280x720 --no-banner {path}'
		#self.logger.debug(cmd)

		result = {'command': key, f'{key}_name': name, f'{key}_path': path, f'{key}_taken': now.strftime('%Y/%m/%d %H:%M:%S')}

		for i in range(RETRY_CAMERA_MAX):
			ret = subprocess.run(cmd, shell=True)
			self.logger.debug(f"camera process returncode={ret.returncode}.")
			if ret.returncode == 0:
				break
			time.sleep(RETRY_CAMERA_DELAY)

		# The camera command result is success if the target picture file exists.
		is_file = os.path.isfile(path)
		self.logger.info(f"picture path [{path}] is {is_file}")
		result[f'{key}_result'] = is_file
		return result

	def save_picture(self, request):
		self.logger.debug("called")
		if os.path.isfile(request['tmp_picture_path']):
			shutil.move(request['tmp_picture_path'], SAVE_PICTURE_DIR)
			no = self.db_manage.insert_picture({'filename': request['tmp_picture_name'], 'taken': request['tmp_picture_taken']})
			ret = (no > 0)
			message = f"tmp picture[{no}] is saved." if ret else f"failed to save tmp picture[{no}]."
		else:
			ret = False
			message = "tmp picture is not found."

		data = {'command': 'picture'}
		data.update(self.db_manage.get_latest_picture(SAVE_PICTURE_DIR))
		self.websocketd.broadcast(data)
		self.logger.info(message)
		return self.make_result(ret, message, True)

	def delete_picture(self, request):
		self.logger.debug("called")
		if os.path.isfile(request['tmp_picture_path']):
			os.remove(request['tmp_picture_path'])
		return self.make_result(True, "tmp picture is deleted.")

	def pump_auto_start(self, request):
		self.logger.debug("called")
		self.manual_timer_stop()
		self.switcher.start()
		self.websocketd.broadcast({'command': 'pump_status', 'pump_status': 'auto_start', 'seconds': 0})
		return self.make_result(True, "pump start (auto)")

	def pump_auto_stop(self, request):
		self.logger.debug("called")
		self.manual_timer_stop()
		self.switcher.stop()

		data = {'command': 'pump_status', 'pump_status': 'auto_stop', 'seconds': 0}
		self.db_manage.set_pump_status(data)
		self.websocketd.broadcast(data)
		return self.make_result(True, "pump stop (auto)")

	def pump_auto_cycle(self, cycle, seconds):
		status = 'cycle_start' if cycle == True else 'cycle_stop'
		data = {'command': 'pump_status', 'pump_status': status, 'seconds': seconds}
		self.db_manage.set_pump_status(data)
		self.websocketd.broadcast(data)

	def pump_manual_start(self, request):
		self.logger.debug("called")
		# いったん止めて再設定
		self.manual_timer_stop()
		self.switcher.stop()

		seconds = request['seconds']
		self.logger.debug(f"seconds={seconds}")
		self.raspi_ctl.switch_continuous(True)
		self.raspi_ctl.switch_blinking(True)
		if 0 < seconds:
			self.manual_timer_start(seconds)

		data = {'command': 'pump_status', 'pump_status': 'manual_start', 'seconds': seconds}
		self.db_manage.set_pump_status(data)
		self.websocketd.broadcast(data)
		return self.make_result(True, "pump start (manual)")

	def pump_manual_stop(self, request):
		self.logger.debug("called")
		self.manual_timer_stop()
		self.switcher.stop()

		data = {'command': 'pump_status', 'pump_status': 'manual_stop', 'seconds': 0}
		self.db_manage.set_pump_status(data)
		self.websocketd.broadcast(data)
		return self.make_result(True, "pump stop (manual)")

	def manual_timer_start(self, seconds):
		self.logger.debug("called")
		self.logger.info(f"timer start seconds={seconds}")
		self.manual_timer = threading.Timer(seconds, self.pump_manual_stop, args=(None, ))
		self.manual_timer.start()

	def manual_timer_stop(self):
		self.logger.debug("called")
		self.raspi_ctl.switch_continuous(False)
		self.raspi_ctl.switch_blinking(False)

		if self.manual_timer != None:
			self.manual_timer.cancel()
			del self.manual_timer
			self.manual_timer = None

	def set_led(self, request):
		ret = self.raspi_ctl.update_led(request['color'])
		return self.make_result(ret, f"led is changed to {request['color']}." )

	def measure_sensor(self, request):
		value = self.raspi_ctl.measure_sensor(request['sensor_kind'])
		if value is None:
			message = f"{request['sensor_kind']} could not read."
			ret = False
		else:
			message = f"{value}"
			ret = True
		return self.make_result(ret, message)

	def subpump_trigger_switch(self, request):
		self.logger.debug("called")
		perform_refill = False
		if request != None and request['option'] == "must":
			perform_refill = not self.raspi_ctl.check_float_upper()
		else:
			perform_refill = not self.raspi_ctl.check_float_lower()

		if perform_refill:
			available = self.raspi_ctl.subpump_available()
			if available:
				level = self.raspi_ctl.measure_water_level()['water_level']
				self.future_subpump = self.executor_subpump.submit(self.subpump_main_switch, level)
				message = "水位低下 サブポンプ動作開始"
			else:
				message = "## 危険 ## 水位低下、サブタンクの水がありません。"
				self.line_notify(message)
		else:
			message = "水位問題なし"
		self.logger.debug(message)

	def subpump_main_switch(self, level_before):
		self.logger.debug("called")

		self.websocketd.broadcast(self.subpump_status_command(True))
		result = self.raspi_ctl.subpump_exec(self.schedule['refill_min'], self.schedule['refill_max'])
		message = f"{result['past']}秒間、水を追加しました。"
		if result['empty'] == True:
			message += "サブタンクの水がなくなりました\n"

		upper = self.raspi_ctl.check_float_upper()
		lower = self.raspi_ctl.check_float_lower()
		subp = self.raspi_ctl.subpump_available()
		level_after = self.raspi_ctl.measure_water_level()['water_level']

		message += f"水位低下→上:{upper} 下:{lower} 補:{subp} （{level_before}％→{level_after}％）"
		self.logger.debug(message)
		self.line_notify(message)
		self.websocketd.broadcast(self.make_result(True, message))

		data = {'refilled_at': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'on_seconds':  result['past'], 'trig': 'switch',
			'upper': 1 if upper is True else 0, 'lower': 1 if lower is True else 0, 'subp': 1 if subp is True else 0,
			'level_before': level_before, 'level_after': level_after}
		self.db_manage.insert_refill_record(data)

		data = self.subpump_status_command()
		data.update(self.db_manage.get_latest_refill_record())
		self.websocketd.broadcast(data)
		return True

	def subpump_trigger_level(self):
		self.logger.debug("called")

		data = self.raspi_ctl.measure_water_level()
		level = data['water_level']
		distance = data['distance']
		if None == level:
			self.logger.info("could not get water_level")
		else:
			self.logger.info(f"water_level = {level}%")

		if None == distance or 0 == distance:
			message = f"水位測定失敗 distance={distance}"
		else:
			limit = self.db_manage.get_sensor_limit()

			if level < limit['water_level_vlow']:
				if self.prev_level != None and self.prev_level < limit['water_level_low']:
					available = self.raspi_ctl.subpump_available()
					if available:
						self.future_subpump = self.executor_subpump.submit(self.subpump_main_level, level)
						message = f"水位{level}％ サブポンプ動作開始"
					else:
						message = f"## 危険 ## 水位{level}％、サブタンクの水がありません。"
						self.line_notify(message)
				else:
					message = f"水位{level}％、次回補充（前回値{self.prev_level}％）"
			elif level < limit['water_level_low']:
				message = f"水位{level}％、次回補充"
			else:
				message = f"水位{level}％、問題なし"

		self.prev_level = level
		self.logger.debug(message)

	def subpump_main_level(self, level_before):
		self.logger.debug("called")

		seconds = self.schedule['refill_max'] - level_before
		if seconds < self.schedule['refill_min']:
			seconds = self.schedule['refill_min']
		self.logger.debug(f"seconds={seconds}")

		self.websocketd.broadcast(self.subpump_status_command(True))
		result = self.raspi_ctl.subpump_exec(self.schedule['refill_min'], seconds)
		message = f"{result['past']}秒間、水を追加しました。"
		if result['empty'] == True:
			message += "サブタンクの水がなくなりました\n"

		level_after = self.raspi_ctl.measure_water_level()['water_level']
		level_plus = level_after - level_before
		message += f"水位{level_before}％→{level_after}％（{level_plus:+}％）"
		self.logger.debug(message)

		self.line_notify(message)
		self.websocketd.broadcast(self.make_result(True, message))

		data = {'refilled_at': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'on_seconds':  result['past'],
			'trig': 'level', 'level_before': level_before, 'level_after': level_after}
		self.db_manage.insert_refill_record(data)

		data = self.subpump_status_command()
		data.update(self.db_manage.get_latest_refill_record())
		self.websocketd.broadcast(data)
		self.prev_level = level_after
		return True

	def subpump_update(self, request=None):
		self.logger.debug("called")
		level_active = True
		if request is not None:
			level_active = True if int(request['level_active']) else False

		return self.subpump_status_command(False, level_active)

	def subpump_status_command(self, force_on=False, level_active=True):
		data = {'command': 'refill_update'}
		data.update(self.subpump_status(force_on, level_active))
		return data

	def subpump_status(self, force_on=False, level_active=True):
		data = {}
		data['refill_switch'] = force_on or self.raspi_ctl.subpump_working
		data['refill_float_upper'] = self.raspi_ctl.check_float_upper()
		data['refill_float_lower'] = self.raspi_ctl.check_float_lower()
		data['refill_float_sub'] = self.raspi_ctl.subpump_available()
		if level_active:
			data['refill_level'] = self.raspi_ctl.measure_water_level()['water_level']
		return data

	def subpump_start(self, request):
		self.logger.debug("called")
		ret = False
		if not self.raspi_ctl.subpump_working:
			self.future_subpump = self.executor_subpump.submit(self.subpump_manual, request)
			ret = True

		return self.make_result(ret, "subpump switch on")

	def subpump_stop(self, request=None):
		self.logger.debug("called")

		ret = self.raspi_ctl.subpump_cancel()
		if ret is True:
			self.future_subpump.result()

		if request is not None:
			return self.make_result(ret, "subpump switch off")

	def subpump_lap(self):
		self.websocketd.broadcast(self.subpump_status_command(True))

	def subpump_manual(self, request):
		self.logger.debug("called")
		result = self.raspi_ctl.subpump_exec(self.schedule['refill_min'], SUBPUMP_MANUAL_SECONDS, self.subpump_lap)
		self.websocketd.broadcast(self.subpump_update(request))
		self.logger.debug("end")
		return True

	def make_result(self, ret, message, popup=False):
		result = "success" if ret == True else "failed"
		ret = {'command': 'result', 'result': result, 'message': message,
			'datetime': datetime.now().strftime('%Y/%m/%d %H:%M:%S')}
		if popup == True:
			ret['show_popup'] = 1
		return ret

	def tweet(self, message, filename=None):
		self.logger.info("called")
		token = self.db_manage.get_sns_token()
		consumer_key = token['twitter_api_key']
		consumer_secret = token['twitter_api_secret_key']
		access_token = token['twitter_access_token']
		access_token_secret = token['twitter_access_token_secret']

		try:
			client = tweepy.Client(
				consumer_key = consumer_key,
				consumer_secret = consumer_secret,
				access_token = access_token,
				access_token_secret = access_token_secret)

			if filename is None:
				self.logger.info("create_tweet without media")
				client.create_tweet(text = message) 
			else:
				self.logger.info("create_tweet with media")
				auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
				auth.set_access_token(access_token, access_token_secret)
				api = tweepy.API(auth)
				media = api.media_upload(filename=filename)
				client.create_tweet(text = message, media_ids = [media.media_id]) 
			return True

		except Exception as e:
			self.logger.error(f"Unknown exception: {e}")
			return False

	def line_notify(self, message, filename=None):
		self.logger.info("called")
		token = self.db_manage.get_sns_token()

		try:
			# line api
			payload = {'message': message}
			headers = {'Authorization': 'Bearer ' + token['line_access_token']}
			files = {}
			if filename != None:
				files['imageFile'] = open(filename, "rb")
			response = requests.post('https://notify-api.line.me/api/notify', data=payload, headers=headers, files=files)
			self.logger.info(response.text)
			return True

		except Exception as e:
			self.logger.error(f"Unknown exception: {e}")
			return False

	def test_tweet(self, request):
		filename = None
		if (request['option'] == 'pic'):
			data = self.db_manage.get_latest_picture(SAVE_PICTURE_DIR)
			filename = data['picture_path']
		now = datetime.now()
		ret = self.tweet("websocketサーバーからのtweetテスト : " + now.strftime('%Y/%m/%d %H:%M:%S'), filename)
		return self.make_result(ret, "tweet test")

	def test_line(self, request):
		message = self.line_notify("websocketサーバーからのlineテスト")
		return self.make_result(True, message)
	
	def test_ssr1(self, request):
		control = request['option']
		message = f"SSR circulator:{control}"
		self.raspi_ctl.circulator_switch(True if control=="on" else False)
		return self.make_result(True, message)

	def test_ssr2(self, request):
		control = request['option']
		message = f"SSR nightly:{control}"
		self.raspi_ctl.nightly_switch(True if control=="on" else False)
		return self.make_result(True, message)

	def debug_time_span(self, request):
		global MINUTE_START
		global MINUTE_STOP
		global MINUTE_REFILL
		MINUTE_START  = int(request['minute_start'])
		MINUTE_STOP   = int(request['minute_stop'])
		MINUTE_REFILL = int(request['minute_refill'])
		self.scheduler_stop()
		self.scheduler_start()
		message = f"changed time span to {MINUTE_START}-{MINUTE_STOP}-{MINUTE_REFILL}"
		self.logger.debug(message)
		return self.make_result(True, message)
	
	def debug_echo(self, request):
		return self.make_result(True, "echo from web socket server.")

class CHydroWebsocketd:
	logger = None
	clients = None
	main_ctl = None

	def __init__(self, logger, main_ctl):
		self.logger = logger
		self.logger.debug("called")
		self.clients = set()
		self.main_ctl = main_ctl

	def __del__(self):
		self.logger.debug("called")

	async def websocket_server(self):
		self.logger.info("websocket server start")
		try:
			async with websockets.serve(self.handler, "", 10700) as wss:
				await wss.wait_closed()

		except asyncio.CancelledError as e:
			self.logger.info("------------------------------")
			self.logger.info("websocket server cancelled")
		finally:
			self.logger.info("websocket server end")

	async def handler(self, client, path):
		self.clients.add(client)
		count = len(self.clients)
		self.logger.info(f"new client connected. clients={count}")
		data = self.main_ctl.get_initial_data()
#		self.logger.debug(json.dumps(data))
		await client.send(json.dumps(data))
		try:
			async for message in client:
				request = json.loads(message)
				response = self.main_ctl.handle_request(request)

				if isinstance(response, asyncio.Future):
					self.logger.debug("awaiting future ...")
					response = await response
					self.logger.debug("awaiting future ... done")

#				self.logger.debug(json.dumps(response))
				await client.send(json.dumps(response))
		except asyncio.CancelledError:
			self.logger.warning("cancelled error.")
		except websockets.exceptions.ConnectionClosedError:
			self.logger.info("connection closed error.")
		finally:
			self.clients.remove(client)
			count = len(self.clients)
			self.logger.info(f"client left. clients={count}")

	def broadcast(self, data):
		self.logger.debug(f"called. command={data['command']}")
#		self.logger.debug(f"called {data}")
		if isinstance(data, dict):
			websockets.broadcast(self.clients, json.dumps(data))
		else:
			self.logger.warning("broadcast data is not dict")
			websockets.broadcast(self.clients, data)

# loggerの設定
def setup_logger(name, logfile):
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)
#	logger.setLevel(logging.INFO)

	log_formatter = logging.Formatter('%(asctime)s: [%(levelname)s] %(filename)s/%(threadName)s - %(funcName)s(%(lineno)s) %(message)s')

#	fh = logging.FileHandler(logfile)
	fh = logging.handlers.RotatingFileHandler(f"log/{logfile}", maxBytes=102400, backupCount=10)
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(log_formatter)

	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	ch.setFormatter(log_formatter)

	logger.addHandler(fh)
	logger.addHandler(ch)

	return logger

class TerminatedExecption(Exception):
	pass

def raise_exception(*_):
	raise TerminatedExecption()

# プログラムスタート
if __name__ == '__main__':
	signal.signal(signal.SIGTERM, raise_exception)
	logger = setup_logger('hydro_websocketd', 'hydro_webs_log.txt')

	logger.info("##### server start #####")
	main_ctl = CHydroMainController(logger)
	main_ctl.start()

	try:
		logger.info("server run")
		main_ctl.run_server()
		logger.info("server halt")

	# Ctrl-Cによるキーボード割り込みで終了
	except KeyboardInterrupt:
		logger.info("### hydro_server ended. (KeyboardInterrupt)")
	# systemdのstopコマンドで終了
	except TerminatedExecption:
		logger.info("### hydro_server ended. (systemd stop)")
	except Exception as e:
		import traceback
		traceback.print_exc()
	finally:
		main_ctl.stop()
		del main_ctl
		logger.info("##### server end #####")

# end.

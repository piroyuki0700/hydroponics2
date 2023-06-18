#!/usr/bin/python3
#
# データベース操作モジュール
#
import mariadb
from datetime import datetime
from datetime import timedelta
import sys
import threading

import logging
import json

#DATABASE_ID = 'hydro2023summer'
DATABASE_ID = 'hydro2023test'

class CHydroDatabaseManager():
	logger = None
	conn = None
	lock_db = None

	def __init__(self, logger):
		self.logger = logger
		try:
			# Connect to MariaDB Platform
			self.conn = mariadb.connect(
				user = 'hydroponics',
				password = 'hydro0700',
				host = 'localhost',
				port = 3306,
				database = DATABASE_ID
			)
			self.conn.auto_reconnect = True
		except mariadb.Error as e:
			self.logger.error(f"mariadb.Error: {e}")
			sys.exit(1)
		self.lock_db = threading.Lock()

	def __del__(self):
		# Close Connection
		self.conn.close()
		del self.lock_db

	def exec(self, sql):
		with self.lock_db:
			try:
				cur = self.conn.cursor()
				cur.execute(sql)
				cur.close()
				self.conn.commit()
				return True
	
			except mariadb.Error as e:
				self.logger.error(f"mariadb.Error: {e}")
				return False

	def getcolumn(self, table, column):
		with self.lock_db:
			try:
				cur = self.conn.cursor()
				columns = ','.join(column)
				sql = f"select {columns} from {table} where no = 1"
				cur.execute(sql)
				row = cur.fetchone()
				cur.close()
	
				dic = {}
				for i in range(1, len(row)):
					if isinstance(row[i], datetime):
						dic[column[i]]=row[i].strftime('%Y/%m/%d %H:%M:%S')
					else:
						dic[column[i]]=row[i]
				return dic
	
			except mariadb.Error as e:
				self.logger.error(f"mariadb.Error: {e}")
				return ""

	def getkeys(self, cur, table):
		sql = f"desc {table}"
		cur.execute(sql)
		keys = []
		for row in cur.fetchall():
			keys.append(row[0])

		return keys

	def getone(self, table):
		data = self.get(table, "where no = 1")
		if len(data) >= 1:
			return data[0]
		else:
			return {}

	def getlatest(self, table, num = 1):
		data = self.get(table, f"order by no desc limit {num}")
		if num == 1:
			if len(data) >= 1:
				return data[0]
			else:
				return {}
		else:
			return data

	def get(self, table, condition = None):
		with self.lock_db:
			try:
				cur = self.conn.cursor()
				keys = self.getkeys(cur, table)
	
				if condition is None:
					sql = f"select * from {table}"
				else:
					sql = f"select * from {table} {condition}"
	
				#print(sql)
				cur.execute(sql)
	
				dic_array = []
				for row in cur.fetchall():
					dic = {}
					for i in range(1, len(row)):
						if isinstance(row[i], datetime):
							dic[keys[i]]=row[i].strftime('%Y/%m/%d %H:%M:%S')
						else:
							dic[keys[i]]=row[i]
					dic_array.append(dic)
				cur.close()

				if len(dic_array) == 0:
					dic_array = []
				return dic_array
	
			except mariadb.Error as e:
				self.logger.error(f"mariadb.Error: {e}")
				return []

	def insert(self, table, data):
		with self.lock_db:
			try:
				cur = self.conn.cursor()
				keys = self.getkeys(cur, table)
	
				column = []
				value = []
				for key in keys:
					if key in data:
						column.append(key)
						value.append(f"'{data[key]}'")
	
				columns = ','.join(column)
				values = ','.join(value)
				sql = f"insert into {table} ({columns}) values ({values})"
				#self.logger.debug(sql)
	
				cur.execute(sql)
				cur.close()
				self.conn.commit()
	
				return cur.lastrowid
	
			except mariadb.Error as e:
				self.logger.error(f"mariadb.Error: {e}")
				return -1

	def updateone(self, table, data):
		with self.lock_db:
			try:
				cur = self.conn.cursor()
				keys = self.getkeys(cur, table)
	
				column = []
				for key in keys:
					if key in data:
						column.append(f"{key} = '{data[key]}'")
	
				columns = ','.join(column)
				sql = f"update {table} set {columns} where no = 1"
				#self.logger.debug(sql)
				cur.execute(sql)
				cur.close()
				self.conn.commit()
				return True
	
			except mariadb.Error as e:
				self.logger.error(f"mariadb.Error: {e}")
				return False

	def get_basic(self):
		self.logger.debug("called")
		basic = self.getone('setting_basic')
		# データベース名を追加
		basic['myid'] = DATABASE_ID
		return basic

	def get_schedule(self):
		self.logger.debug("called")
		return self.getone('setting_schedule')

	def get_sensor_limit(self):
		self.logger.debug("called")
		return self.getone('setting_sensor_limit')

	def get_latest_picture(self, picture_dir):
		self.logger.debug("called")
		result = self.getlatest('picture')
		if len(result) == 0:
			return {}
		return {'picture_path': f"{picture_dir}/{result['filename']}", 'picture_taken': result['taken']}

	def get_latest_report(self):
		self.logger.debug("called")
		return self.getlatest('report')

	def make_refill_record_string(self, data):
		if data['trig'] == "level":
			result = f"{data['refilled_at']}({data['on_seconds']} sec) {data['level_before']}%→{data['level_after']}%"
		else:
			upper = 'o' if data['upper'] == 1 else 'x'
			lower = 'o' if data['lower'] == 1 else 'x'
			result = f"{data['refilled_at']}({data['on_seconds']} sec) 上:{upper} 下:{lower}"
		return result

	def get_latest_refill_record(self):
		self.logger.debug("called")
		dic_array = self.getlatest('refill_record', 3)
		result = {}
		if (len(dic_array) >= 1):
			result['refill_record1'] = self.make_refill_record_string(dic_array[0])
		if (len(dic_array) >= 2):
			result['refill_record2'] = self.make_refill_record_string(dic_array[1])
		if (len(dic_array) >= 3):
			result['refill_record3'] = self.make_refill_record_string(dic_array[2])
		return result

	def set_basic(self, data):
		self.logger.debug("called")
		now = datetime.now()
		setdata = {f"{data['kind']}ed": now.strftime('%Y/%m/%d %H:%M:%S')}
		return self.updateone('setting_basic', setdata)

	def set_schedule(self, data):
		self.logger.debug("called")
		return self.updateone('setting_schedule', data)

	def set_sensor_limit(self, data):
		self.logger.debug("called")
		return self.updateone('setting_sensor_limit', data)

	def get_sns_token(self):
		self.logger.debug("called")
		return self.getone('sns_token')

	def get_twitter_token(self):
		self.logger.debug("called")
		return self.getcolumn('sns_token', ('twitter_api_key', 'twitter_api_secret_key', 'twitter_access_token', 'twitter_access_token_secret'))

	def set_pump_status(self, data):
		self.logger.debug("called")
		end_time = datetime.now() + timedelta(seconds = data['seconds'])
		return self.updateone('pump_status', {'status': data['pump_status'], 'end_time': end_time.strftime("%Y/%m/%d %H:%M:%S")})

	def get_pump_status(self):
		self.logger.debug("called")
		row = self.getone('pump_status')
		if len(row) == 0:
			seconds = 0
			row['status'] = 'manual_stop'
		else:
			end = datetime.strptime(row['end_time'], '%Y/%m/%d %H:%M:%S')
			tdiff = end - datetime.now()
			seconds = tdiff.total_seconds()
			if seconds < 0:
				# 過去の時刻が入っていた場合
				seconds = 0
				row['status'] = 'error_stop'
		data = {'pump_status': row['status'], 'seconds': seconds}
#		self.logger.debug(f"{data}")
		return data

	def insert_picture(self, data):
		self.logger.debug("called")
		return self.insert("picture", data)

	def insert_report(self, data):
		self.logger.debug("called")
		return self.insert("report", data)

	def insert_refill_record(self, data):
		self.logger.debug("called")
		return self.insert("refill_record", data)
	
	def countup_sensor_error(self, sensor, limit):
		self.logger.debug("called")
		over_limit = False
		data = self.getone("sensor_error")
		data[sensor] += 1
		if data[sensor] == limit:
			data[sensor] = 0
			over_limit = True
		self.updateone("sensor_error", data)
		return over_limit

#
# テスト用
#
if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)

	mydb = CHydroDatabaseManager(logger)
	dic = mydb.getlatest('setting_basic')
	del mydb
	logger.info(json.dumps(dic))



import datetime
import time

START_TIME = str(datetime.datetime.now())

START_TIME2 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))


print(time.gmtime(time.time()))

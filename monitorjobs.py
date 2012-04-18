import sys
import subprocess 
import re
import time
import datetime
import os
import MySQLdb

# Email only works with 2.5 or higher right now
if sys.version_info[1] > 4:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText


class MonitorAlert:
    "Base Class for alerts"
    def __init__(self, dest = sys.stdout):
        self.destination = dest

    def logAlert(self, message, jobName = None):
        print >> self.destination, message

    def register(self, jobName = None):
        pass

    def updateStatus(self, status, jobName):
        pass

    def finish(self):
        "Used for alert handlers that queue up all of the alerts and send them together"
        pass

class ConsoleAlert(MonitorAlert):
    def __init__(self):
        MonitorAlert.__init__(self)

class FileAlert(MonitorAlert):
    def __init__(self, fileName, includeTime = False):
	self.file = open(fileName, 'a')
	self.time = includeTime

    def logAlert(self, message, jobName = None):
	if self.time:
		self.file.write(time.strftime("%m/%d/%y %H:%M:%S: ", time.localtime()))
	self.file.write(message + '\r\n')

    def finish(self):
	self.file.close()

class EmailAlert(MonitorAlert):
    def __init__(self, toUser, server = "localhost", fromUser = "alert@localhost", subject = "System Monitor Alert!"):
        MonitorAlert.__init__(self)
        self.message = []
        self.subject = subject
        self.server = server
        self.fromUser = fromUser
        self.toUser = toUser

    def logAlert(self, message, jobName = None):
        self.message.append(message)

    def finish(self):
	if len(self.message) > 0:
        	self.sendMail()

    def sendMail(self):
        if sys.version_info[1] > 4:
            messageText = '\r\n'.join(self.message) 
            msg = MIMEMultipart()
            msg['Subject'] = self.subject
            msg['From'] = self.fromUser
            msg['To'] = self.toUser
            msg.attach(MIMEText(messageText, 'plain'))
            server = smtplib.SMTP(self.server)
            server.sendmail(self.fromUser, [self.toUser], msg.as_string())
            server.quit()     
        else:
            print "Email only works with python 2.5 or higher right now"   

class JobListMonitor(MonitorAlert):
    def __init__(self, dest = sys.stdout):
        self.jobs = []
        self.destination = dest

    def register(self, jobName = None):
        self.jobs.append(jobName)

    def finish(self):
        print >> self.destination, " ".join(self.jobs)


class MonitorJob :
    "Base Class for all jobs"
    def __init__(self, jobname, alert = None):
        self.name = jobname
        self.alerts = []
        if alert is not None:
            self.addAlert(alert)
    
    def logAlert(self, message):
        [al.logAlert(message, self.name) for al in self.alerts];
        
    def addAlert(self, alert):
        self.alerts.append(alert)
        alert.register(self.name)

    def updateStatus(self, status):
        [al.updateStatus(status, self.name) for al in self.alerts];

    def run(self):
        self.logAlert("Run is undefined")

class Monitor:
    "Configures and executes all of the monitoring jobs"
    def __init__(self,  defaultAlert = None):
        self.jobs = []
        self.alerts = []
        if defaultAlert is not None:
            self.alerts.append(defaultAlert)
    
    def addJob(self, job):
        if self.alerts is not None:
            for alert in self.alerts:
                job.addAlert(alert)
        self.jobs.append(job)

    def addAlert(self, alert):
        for job in self.jobs:
            job.addAlert(alert)
        self.alerts.append(alert)

    def execute(self):
        [job.run() for job in self.jobs]
        for alert in self.alerts:
            alert.finish()

class PingJob(MonitorJob):
    def __init__(self, destination, alert = None, pings = 4, threshold = 80):
        MonitorJob.__init__(self, "Ping %s" % (destination,), alert)
        self.dest = destination
        self.pings = pings
        self.threshold = threshold

    def run(self):
        self.doPing()

    def performPing(self):
        ping = subprocess.Popen(["ping", "-c", "4", self.dest], stdout = subprocess.PIPE)
        out, error = ping.communicate()
        reResult = re.compile(r'(\d+)% packet loss').search(out).groups()
        if reResult is None:
            self.logAlert("Unable to find ping result")
            return 0

        percent = int(reResult[0])
	return percent

    def doPing(self):
	percent = self.performPing()
        if percent > self.threshold:
            self.logAlert("Host %s Is Not Responding" % self.dest)

class NoResponsePingJob(PingJob):
    def doPing(self):
        percent = self.performPing()
        if percent < 100:
            self.logAlert("Host %s Is Up and Reponding To Pings" % self.dest)


class CheckProcessJob(MonitorJob):
    def __init__(self, process, alert = None):
        MonitorJob.__init__(self, "Check Process %s" % (process,), alert)
        self.process = process
    
    def run(self):
        self.checkProcess()

    def checkProcess(self):
        ps = subprocess.Popen(["ps", "-e"], stdout = subprocess.PIPE)
        out, error = ps.communicate()
        reString = self.process
        psRe = re.compile(reString)
        
        if psRe.search(out) is None:
            self.logAlert("Process %s Is Not Running" % self.process)

class CheckMySQLDatabaseJob(MonitorJob):
    def __init__(self, name, query, user, password, database, host = 'localhost', alert = None):
        MonitorJob.__init__(self, "Check MySQL Database: %s" % (name), alert)
        self.host = host
        self.query = query
        self.user = user
        self.password = password
        self.database = database
        self.queryName = name

    def run(self):
        self.checkDb()

    def checkDb(self):
        db = MySQLdb.connect(self.host, self.user, self.password, self.database)
        cursor = db.cursor()
        result = cursor.execute(self.query)
        if result > 0:
            row = cursor.fetchone()
            self.logAlert("Query %s returned result: %s" % (self.queryName, row[0]))
        db.close()

class CheckDiskSpaceJob(MonitorJob):
    def __init__(self, path, minimumPercent, alert = None):
        MonitorJob.__init__(self, "Check Disk Space %s" % (path), alert)
        self.path = path
        self.percent = minimumPercent

    def run(self):
        self.checkThreshold() 

    def checkThreshold(self):
        stats = os.statvfs(self.path)
        free = float(stats.f_bsize * stats.f_bavail)
        total = float(stats.f_bsize * stats.f_blocks)
        ratio = free/total
        self.updateStatus("Space Available: %d MB - %d percent" % (free / 1000000, ratio * 100))
        if ratio < (float(self.percent) / 100):
            self.logAlert("Disk Space On %s Is Below Threshold %s percent" % (self.path, self.percent))

class FileExistsJob(MonitorJob):
    def __init__(self, path, name=None, alert=None):
        jobName = "File %s Exists" % (path)
        if name is not None:
            jobName = name
        MonitorJob.__init__(self, jobName, alert)
        self.path = path

    def _checkPath(self):
        return os.path.exists(self.path)

    def run(self):
        if not self._checkPath():
            self.logAlert("%s Does Not Exist" % (self.path))

class ScanLogsJob(MonitorJob):
    def __init__(self, logfile, text, sinceTime = None, alert = None):
        "Note: sinceTime is in minutes"
        MonitorJob.__init__(self, "Scan Logs %s - %s" % (logfile, text), alert)
        self.logfile = logfile
        self.text = text
        self.sinceTime = sinceTime

    def parseDate(self, line):
        dateFormats = [self.parseDate1, self.parseDate2]       
        dates = [fun(line) for fun in dateFormats]
        goodDates = [d for d in dates if d is not None]
        if len(goodDates) > 0:
            return goodDates[0]
        return None
    
    def parseDate1(self, line):
        dateRe = re.compile('(\w{3} \d+ \d{2}:\d{2}:\d{2})')
        dateText = self.findDate(dateRe, line)
        if dateText is None:
            return None
        parsed = time.strptime(dateText, "%b %d %H:%M:%S")[1:6]
        logdate = []
        logdate.append(time.localtime()[0])
        logdate.extend(parsed)
        convDate = datetime.datetime(*logdate)
        return convDate 
        
    def parseDate2(self, line):
        dateRe = re.compile('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        dateText = self.findDate(dateRe, line)
        if dateText is None:
            return None
        convDate = datetime.datetime(*time.strptime(dateText, "%Y-%m-%d %H:%M:%S")[0:6])
        return convDate 

    def findDate(self, dateRe, line):
        dateSearch = dateRe.search(line)
        if dateSearch is None:
            return None
        return dateSearch.groups()[0]

    def run(self):
        ping = subprocess.Popen(["grep", self.text, self.logfile ], stdout = subprocess.PIPE)
        out, error = ping.communicate()
        if out.find(self.text) == -1:
            return
        dateInRange = True
        if self.sinceTime is not None:
            dateInRange = self.isDataSince(out)
        if dateInRange:
            self.logAlert("Found Message In The Logs: \n" + out)

    def isDataSince(self, out):
        lines = out.split("\n")
        dates = [self.parseDate(line) for line in lines]
        now = datetime.datetime(*time.localtime()[0:6])
        diff = datetime.timedelta(minutes = self.sinceTime)
        thresholdDate = now - diff
        for date in dates:
            if date is not None and date > thresholdDate:
                return True

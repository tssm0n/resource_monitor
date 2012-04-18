import unittest
import monitorjobs
import os

class MonitorJobTest(unittest.TestCase):
    class AlertMock(monitorjobs.MonitorAlert):
        def __init__(self):
            self.alerted = False
            
        def logAlert(self, message, jobName = None):
            if message == "Test Alert":
                self.alerted = True 

    class AnyAlertMock(monitorjobs.MonitorAlert):
        def __init__(self):
            self.alerted = False

        def logAlert(self, message, jobName = None):
            self.alerted = True 

    class JobMock(monitorjobs.MonitorJob):
        def run(self):
            self.logAlert("Test Alert")

    class OutputMock:
        def __init__(self):
            self.output = ""

        def write(self, val):
            self.output = self.output + val;

    def testLogAlert(self):
        alert1 = MonitorJobTest.AlertMock()
        alert2 = MonitorJobTest.AlertMock()
        job = monitorjobs.MonitorJob("testjob", alert1)
        job.addAlert(alert2)
        job.logAlert("Test Alert")
        self.assertTrue(alert1.alerted)
        self.assertTrue(alert2.alerted)
        
    def testRegister(self):
        output = MonitorJobTest.OutputMock() 
        alert1 = monitorjobs.JobListMonitor(output)
        job = monitorjobs.MonitorJob("testjob", alert1)
        #job.logAlert("Test Alert")
        alert1.finish() 
        self.assertEquals(output.output, "testjob\n")

    def testMonitor(self):
        alert1 = MonitorJobTest.AlertMock()
        alert2 = MonitorJobTest.AlertMock()
        job1 = MonitorJobTest.JobMock("testjob",  alert1)
        job2 = MonitorJobTest.JobMock("testjob2", alert2)
        monitor = monitorjobs.Monitor()
        monitor.addJob(job1)
        monitor.addJob(job2)
        monitor.execute()
        self.assertTrue(alert1.alerted)
        self.assertTrue(alert2.alerted)

    def testPingJob(self):
        alert1 = MonitorJobTest.AnyAlertMock()   
        ping = monitorjobs.PingJob("localhost", alert1)
        ping.run()
        self.assertFalse(alert1.alerted)        

    def testPingJobFail(self):
        alert1 = MonitorJobTest.AnyAlertMock()
        ping = monitorjobs.PingJob("10.10.10.10", alert1)
        ping.run()
        self.assertTrue(alert1.alerted)

    def testNoResponsePingJob(self):
	alert1 = MonitorJobTest.AnyAlertMock()
	ping = monitorjobs.NoResponsePingJob("10.10.10.10", alert1)
	ping.run()
	self.assertFalse(alert1.alerted)

    def testNoResponsePingJobFile(self):
        alert1 = MonitorJobTest.AnyAlertMock()
        ping = monitorjobs.NoResponsePingJob("localhost", alert1)
        ping.run()
        self.assertTrue(alert1.alerted)


    def testCheckProcessJob(self):
        alert1 = MonitorJobTest.AnyAlertMock()
        ps = monitorjobs.CheckProcessJob("python", alert1)
        ps.run()
        self.assertFalse(alert1.alerted)

    def testCheckProcessJobFail(self):
        alert1 = MonitorJobTest.AnyAlertMock()
        ps = monitorjobs.CheckProcessJob("asdadaw22adasdasdda22", alert1)
        ps.run()
        self.assertTrue(alert1.alerted)

    def testScanLogsParseDate1(self):
        job = monitorjobs.ScanLogsJob("","")
        goodline = 'Jan 13 07:10:43 - asdasd'
        badline = '1209ad12  12-asd12'
        result1 = job.parseDate1(goodline)
        result2 = job.parseDate1(badline)
        self.assert_(result1 is not None)
        self.assert_(result2 is None)

    def testScanLogsParseDate2(self):
        job = monitorjobs.ScanLogsJob("","")
        goodline = '2010-01-13 07:48:34.704 - asdasd'
        badline = '1209ad12  12-asd12'
        result1 = job.parseDate2(goodline)
        result2 = job.parseDate2(badline)
        self.assert_(result1 is not None)
        self.assert_(result2 is None)

    def testScanLogsParseDate(self):
        job = monitorjobs.ScanLogsJob("","")
        goodline = '2010-01-13 07:48:34.704 - asdasd'
        badline = '1209ad12  12-asd12'
        goodline2 = 'Jan 13 07:10:43 - asdasd'
        result1 = job.parseDate(goodline)
        result2 = job.parseDate(badline)
        result3 = job.parseDate(goodline2)
        self.assert_(result1 is not None)
        self.assert_(result2 is None)
        self.assert_(result3 is not None)

    def testScanLogs(self):
        alert1 = MonitorJobTest.AnyAlertMock()
        testString = "2010-01-13 13:48:34  Something to find"
        job = monitorjobs.ScanLogsJob(logfile = "monitortest.py", text = "Something"+" to find", alert = alert1)
        job.run()
        self.assertTrue(alert1.alerted)
 
        alert2 = MonitorJobTest.AnyAlertMock()
        job = monitorjobs.ScanLogsJob(sinceTime = 120, logfile = "monitortest.py", text = "Something"+" to find", alert = alert2)
        job.run()
        self.assertFalse(alert2.alerted)

    def testFileAlert(self):
        alert = monitorjobs.FileAlert("file1.txt")
        alert.logAlert("ALERT")
        alert.finish()

        found = False
        f1 = open("file1.txt", 'r')
        for line in f1:
            if line == "ALERT\r\n":
                found = True
        f1.close()
        os.remove("file1.txt")
        self.assertTrue(found)

    def _writeTestFile(selfi, file):
        outFile = open(file, 'w')
        outFile.write("ok")
        outFile.close()

    def testCheckPath(self):
        file = "/tmp/heh.test.file"
        job = monitorjobs.FileExistsJob(file)
        actual1 = job._checkPath()
        self._writeTestFile(file)
        actual2 = job._checkPath()
        os.remove(file)
        actual3 = job._checkPath()
        self.assertFalse(actual1)
        self.assertTrue(actual2)
        self.assertFalse(actual3)

    def testFileAlert(self):
        file = "/tmp/heh.test.file"
        alert1 = MonitorJobTest.AnyAlertMock()
        alert2 = MonitorJobTest.AnyAlertMock()
        job = monitorjobs.FileExistsJob(file, alert=alert1)
        actual1 = job.run()
        self.assertTrue(alert1.alerted)
        
        job2 = monitorjobs.FileExistsJob(file, alert=alert2)
        self._writeTestFile(file)
        job2.run()
        self.assertFalse(alert2.alerted)
        os.remove(file)

if __name__ == "__main__":
    unittest.main()   

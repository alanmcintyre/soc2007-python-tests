import asyncore
import socket
import threading
import smtpd
import smtplib
import StringIO
import sys
import time

from unittest import TestCase
from test import test_support


def general_server(evt):
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.settimeout(3)
    serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv.bind(("", 9091))
    serv.listen(5)
    try:
        conn, addr = serv.accept()
    except socket.timeout:
        pass
    else:
        conn.send("220 Hola mundo\n")
        conn.close()
    finally:
        serv.close()
        evt.set()

class GeneralTests(TestCase):

    def setUp(self):
        self.evt = threading.Event()
        threading.Thread(target=general_server, args=(self.evt,)).start()
        time.sleep(.1)

    def tearDown(self):
        self.evt.wait()

    def testBasic1(self):
        # connects
        smtp = smtplib.SMTP("localhost", 9091)
        smtp.sock.close()

    def testBasic2(self):
        # connects, include port in host name
        smtp = smtplib.SMTP("localhost:9091")
        smtp.sock.close()

    def testLocalHostName(self):
        # check that supplied local_hostname is used
        smtp = smtplib.SMTP("localhost", 9091, local_hostname="testhost")
        self.assertEqual(smtp.local_hostname, "testhost")
        smtp.sock.close()

    def testNonnumericPort(self):
        # check that non-numeric port raises ValueError
        self.assertRaises(socket.error, smtplib.SMTP, "localhost", "bogus")

    def testNotConnected(self):
        # connects
        smtp = smtplib.SMTP()
        try:
            smtp.connect('nowhere', -1)
        except:
            pass
        self.assertRaises(smtplib.SMTPServerDisconnected, smtp.send('test'))

    def testTimeoutDefault(self):
        # default
        smtp = smtplib.SMTP("localhost", 9091)
        self.assertTrue(smtp.sock.gettimeout() is None)
        smtp.sock.close()

    def testTimeoutValue(self):
        # a value
        smtp = smtplib.SMTP("localhost", 9091, timeout=30)
        self.assertEqual(smtp.sock.gettimeout(), 30)
        smtp.sock.close()

    def testTimeoutNone(self):
        # None, having other default
        previous = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            smtp = smtplib.SMTP("localhost", 9091, timeout=None)
        finally:
            socket.setdefaulttimeout(previous)
        self.assertEqual(smtp.sock.gettimeout(), 30)
        smtp.sock.close()


# Test server using smtpd.DebuggingServer
def debugging_server(evt):
    serv = smtpd.DebuggingServer(("localhost", 9091), ('nowhere', -1))

    try:
        asyncore.loop(timeout=.01, count=200)
    except socket.timeout:
        pass
    finally:
        asyncore.close_all()
        evt.set()

MSG_BEGIN = '---------- MESSAGE FOLLOWS ----------\n'
MSG_END = '------------ END MESSAGE ------------\n'

# Test behavior of smtpd.DebuggingServer
class DebuggingServerTests(TestCase):

    def setUp(self):
        self.old_stdout = sys.stdout
        self.output = StringIO.StringIO()
        sys.stdout = self.output

        self.evt = threading.Event()
        threading.Thread(target=debugging_server, args=(self.evt,)).start()
        time.sleep(.1)

    def tearDown(self):
        self.evt.wait()
        sys.stdout = self.old_stdout

    def testBasic(self):
        # connect
        smtp = smtplib.SMTP("localhost", 9091)
        smtp.sock.close()

    def testEHLO(self):
        smtp = smtplib.SMTP("localhost", 9091)
        self.assertEqual(smtp.ehlo(), (502, 'Error: command "EHLO" not implemented'))
        smtp.sock.close()

    def testHELP(self):
        smtp = smtplib.SMTP("localhost", 9091)
        self.assertEqual(smtp.help(), 'Error: command "HELP" not implemented')
        smtp.sock.close()

    def testLogin(self):
        self.assertEqual(1,2)

    def testSend(self):
        # connect and send mail
        m = 'A test message'
        smtp = smtplib.SMTP("localhost", 9091)
        smtp.sendmail('John', 'Sally', m)
        smtp.sock.close()

        self.evt.wait()
        self.output.flush()
        mexpect = '%s%s\n%s' % (MSG_BEGIN, m, MSG_END)
        self.assertEqual(self.output.getvalue(), mexpect)



# A server that returns pre-scripted conversations (this is used for testing
# since we don't have a full SMTP server implementation in the standard lib).
def scripted_server(evt, conversation):
    serv = smtpd.DebuggingServer(("localhost", 9091), ('nowhere', -1))

    try:
        asyncore.loop(timeout=.01, count=200)
    except socket.timeout:
        pass
    finally:
        asyncore.close_all()
        evt.set()

# server that gives a bad HELO response
def badhelo_server(evt):
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.settimeout(3)
    serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv.bind(("localhost", 9091))
    serv.listen(5)
    try:
        conn, addr = serv.accept()
    except socket.timeout:
        pass

    try:
        conn.send("199 no hello for you!\n199 no hello for you!\n")
        print 'Received', repr(conn.recv(0))
        conn.close()
    finally:
        serv.close()
        evt.set()

class BadHELOServerTests(TestCase):

    def setUp(self):
        self.old_stdout = sys.stdout
        self.output = StringIO.StringIO()
        sys.stdout = self.output

        self.evt = threading.Event()
        threading.Thread(target=badhelo_server, args=(self.evt,)).start()
        time.sleep(.1)

    def tearDown(self):
        self.evt.wait()
        sys.stdout = self.old_stdout

    def testFailingHELO(self):
        self.assertRaises(smtplib.SMTPConnectError, smtplib.SMTP, "localhost", 9091)

#    def testFailingLogin(self):
#        s = smtplib.SMTP()
#        s.connect('localhost', 9091)
#        self.assertRaises(smtplib.SMTPHeloError, s.login, "nobody", "nowhere")


def test_main(verbose=None):
    test_support.run_unittest(GeneralTests, DebuggingServerTests, BadHELOServerTests)
#    test_support.run_unittest(GeneralTests)

if __name__ == '__main__':
    test_main()

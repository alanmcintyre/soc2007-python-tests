# test asynchat -- requires threading

import thread # If this fails, we can't test this module
import asyncore, asynchat, socket, threading, time
import unittest
from test import test_support

HOST = "127.0.0.1"
PORT = 54322
SERVER_QUIT = 'QUIT\n'

class echo_server(threading.Thread):

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        global PORT
        PORT = test_support.bind_port(sock, HOST, PORT)
        sock.listen(1)
        conn, client = sock.accept()
        buffer = ""
        # collect data until SERVER_QUIT is seen
        while SERVER_QUIT not in buffer:
            data = conn.recv(1)
            if not data:
                break
            buffer = buffer + data

        # remove the SERVER_QUIT message
        buffer = buffer.replace(SERVER_QUIT, '')

        # re-send entire set of collected data
        while buffer:
            n = conn.send(buffer[0])
            time.sleep(0.001)
            buffer = buffer[n:]

        conn.close()
        sock.close()

class echo_client(asynchat.async_chat):

    def __init__(self, terminator):
        asynchat.async_chat.__init__(self)
        self.contents = []
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((HOST, PORT))
        self.set_terminator(terminator)
        self.buffer = ''

    def handle_connect(self):
        pass
        ##print "Connected"

    def collect_incoming_data(self, data):
        self.buffer += data

    def found_terminator(self):
        #print "Received:", repr(self.buffer)
        if not self.buffer:
            self.close()
        else:
            self.contents.append(self.buffer)

        self.buffer = ""


class TestAsynchat(unittest.TestCase):
    usepoll = False

    def setUp (self):
        pass

    def tearDown (self):
        pass

    def line_terminator_check(self, term):
        s = echo_server()
        s.start()
        time.sleep(1) # Give server time to initialize
        c = echo_client(term)
        c.push("hello ")
        c.push("world%s" % term)
        c.push("I'm not dead yet!%s" % term)
        c.push(SERVER_QUIT)
        asyncore.loop(use_poll=self.usepoll)#, count=5, timeout=5)
        s.join()

        self.assertEqual(c.contents, ["hello world", "I'm not dead yet!"])

    def test_line_terminator1(self):
        self.line_terminator_check('\n')

    def test_line_terminator2(self):
        self.line_terminator_check('\r\n')

    def test_line_terminator3(self):
        self.line_terminator_check('qqq')

    def numeric_terminator_check(self, termlen):
        # Try reading a fixed number of bytes
        s = echo_server()
        s.start()
        time.sleep(1) # Give server time to initialize
        c = echo_client(termlen)
        data = "hello world, I'm not dead yet!\n"
        c.push(data)
        c.push(SERVER_QUIT)
        asyncore.loop(use_poll=self.usepoll)#, count=5, timeout=5)
        s.join()

        self.assertEqual(c.contents, [data[:termlen]])

    def test_numeric_terminator1(self):
        # check that ints & longs both work (since type is 
        # explicitly checked in handle_read)
        self.numeric_terminator_check(1)
        self.numeric_terminator_check(1L)

    def test_numeric_terminator2(self):
        self.numeric_terminator_check(6L)

    def test_none_terminator(self):
        # Try reading a fixed number of bytes
        s = echo_server()
        s.start()
        time.sleep(1) # Give server time to initialize
        c = echo_client(None)
        data = "hello world, I'm not dead yet!\n"
        c.push(data)
        c.push(SERVER_QUIT)
        asyncore.loop(use_poll=self.usepoll)#, count=5, timeout=5)
        s.join()

        self.assertEqual(c.contents, [])
        self.assertEqual(c.buffer, data)
    
    def test_simple_producer(self):
        s = echo_server()
        s.start()
        time.sleep(1) # Give server time to initialize
        c = echo_client('\n')
        data = "hello world\nI'm not dead yet!\n"
        p = asynchat.simple_producer(data+SERVER_QUIT, buffer_size=8)
        c.push_with_producer(p)
        asyncore.loop(use_poll=self.usepoll)#, count=5, timeout=5)
        s.join()

        self.assertEqual(c.contents, ["hello world", "I'm not dead yet!"])

    def test_empty_line(self):
        # checks that empty lines are handled correctly
        s = echo_server()
        s.start()
        time.sleep(1) # Give server time to initialize
        c = echo_client('\n')
        c.push("hello world\n\nI'm not dead yet!\n")
        c.push(SERVER_QUIT)
        asyncore.loop(use_poll=self.usepoll)
        s.join()

        self.assertEqual(c.contents, ["hello world", "I'm not dead yet!"])



class TestAsynchat_WithPoll(TestAsynchat):
    usepoll = True

class TestHelperFunctions(unittest.TestCase):
    def test_find_prefix_at_end(self):
        self.assertEqual(asynchat.find_prefix_at_end("qwerty\r", "\r\n"), 1)
        self.assertEqual(asynchat.find_prefix_at_end("qwertydkjf", "\r\n"), 0)

def test_main(verbose=None):
    test_support.run_unittest(TestAsynchat, TestAsynchat_WithPoll,
                              TestHelperFunctions)

if __name__ == "__main__":
    test_main(verbose=True)

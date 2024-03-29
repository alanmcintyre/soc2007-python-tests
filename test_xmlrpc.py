import base64
import datetime
import sys
import threading
import time
import unittest
import xmlrpclib
import SimpleXMLRPCServer
from test import test_support

try:
    unicode
except NameError:
    have_unicode = False
else:
    have_unicode = True

alist = [{'astring': 'foo@bar.baz.spam',
          'afloat': 7283.43,
          'anint': 2**20,
          'ashortlong': 2L,
          'anotherlist': ['.zyx.41'],
          'abase64': xmlrpclib.Binary("my dog has fleas"),
          'boolean': xmlrpclib.False,
          'boolean': xmlrpclib.True,
          'unicode': u'\u4000\u6000\u8000',
          u'ukey\u4000': 'regular value',
          'datetime1': xmlrpclib.DateTime('20050210T11:41:23'),
          'datetime2': xmlrpclib.DateTime(
                        (2005, 02, 10, 11, 41, 23, 0, 1, -1)),
          'datetime3': xmlrpclib.DateTime(
                        datetime.datetime(2005, 02, 10, 11, 41, 23)),
          'datetime4': xmlrpclib.DateTime(
                        datetime.date(2005, 02, 10)),
          'datetime5': xmlrpclib.DateTime(
                        datetime.time(11, 41, 23)),
          }]

class XMLRPCTestCase(unittest.TestCase):

    def test_dump_load(self):
        self.assertEquals(alist,
                          xmlrpclib.loads(xmlrpclib.dumps((alist,)))[0][0])

    def test_dump_bare_datetime(self):
        # This checks that an unwrapped datetime.date object can be handled
        # by the marshalling code.  This can't be done via test_dump_load()
        # since with use_datetime set to 1 the unmarshaller would create
        # datetime objects for the 'datetime[123]' keys as well
        dt = datetime.datetime(2005, 02, 10, 11, 41, 23)
        s = xmlrpclib.dumps((dt,))
        (newdt,), m = xmlrpclib.loads(s, use_datetime=1)
        self.assertEquals(newdt, dt)
        self.assertEquals(m, None)

        (newdt,), m = xmlrpclib.loads(s, use_datetime=0)
        self.assertEquals(newdt, xmlrpclib.DateTime('20050210T11:41:23'))

    def test_dump_bare_date(self):
        # This checks that an unwrapped datetime.date object can be handled
        # by the marshalling code.  This can't be done via test_dump_load()
        # since the unmarshaller produces a datetime object
        d = datetime.datetime(2005, 02, 10, 11, 41, 23).date()
        s = xmlrpclib.dumps((d,))
        (newd,), m = xmlrpclib.loads(s, use_datetime=1)
        self.assertEquals(newd.date(), d)
        self.assertEquals(newd.time(), datetime.time(0, 0, 0))
        self.assertEquals(m, None)

        (newdt,), m = xmlrpclib.loads(s, use_datetime=0)
        self.assertEquals(newdt, xmlrpclib.DateTime('20050210T00:00:00'))

    def test_dump_bare_time(self):
        # This checks that an unwrapped datetime.time object can be handled
        # by the marshalling code.  This can't be done via test_dump_load()
        # since the unmarshaller produces a datetime object
        t = datetime.datetime(2005, 02, 10, 11, 41, 23).time()
        s = xmlrpclib.dumps((t,))
        (newt,), m = xmlrpclib.loads(s, use_datetime=1)
        today = datetime.datetime.now().date().strftime("%Y%m%d")
        self.assertEquals(newt.time(), t)
        self.assertEquals(newt.date(), datetime.datetime.now().date())
        self.assertEquals(m, None)

        (newdt,), m = xmlrpclib.loads(s, use_datetime=0)
        self.assertEquals(newdt, xmlrpclib.DateTime('%sT11:41:23'%today))

    def test_bug_1164912 (self):
        d = xmlrpclib.DateTime()
        ((new_d,), dummy) = xmlrpclib.loads(xmlrpclib.dumps((d,),
                                            methodresponse=True))
        self.assert_(isinstance(new_d.value, str))

        # Check that the output of dumps() is still an 8-bit string
        s = xmlrpclib.dumps((new_d,), methodresponse=True)
        self.assert_(isinstance(s, str))

    def test_newstyle_class(self):
        class T(object):
            pass
        t = T()
        t.x = 100
        t.y = "Hello"
        ((t2,), dummy) = xmlrpclib.loads(xmlrpclib.dumps((t,)))
        self.assertEquals(t2, t.__dict__)

    def test_dump_big_long(self):
        self.assertRaises(OverflowError, xmlrpclib.dumps, (2L**99,))

    def test_dump_bad_dict(self):
        self.assertRaises(TypeError, xmlrpclib.dumps, ({(1,2,3): 1},))

    def test_dump_recursive_seq(self):
        l = [1,2,3]
        t = [3,4,5,l]
        l.append(t)
        self.assertRaises(TypeError, xmlrpclib.dumps, (l,))

    def test_dump_recursive_dict(self):
        d = {'1':1, '2':1}
        t = {'3':3, 'd':d}
        d['t'] = t
        self.assertRaises(TypeError, xmlrpclib.dumps, (d,))

    def test_dump_big_int(self):
        if sys.maxint > 2L**31-1:
            self.assertRaises(OverflowError, xmlrpclib.dumps,
                              (int(2L**34),))

        xmlrpclib.dumps((xmlrpclib.MAXINT, xmlrpclib.MININT))
        self.assertRaises(OverflowError, xmlrpclib.dumps, (xmlrpclib.MAXINT+1,))
        self.assertRaises(OverflowError, xmlrpclib.dumps, (xmlrpclib.MININT-1,))

        def dummy_write(s):
            pass

        m = xmlrpclib.Marshaller()
        m.dump_int(xmlrpclib.MAXINT, dummy_write)
        m.dump_int(xmlrpclib.MININT, dummy_write)
        self.assertRaises(OverflowError, m.dump_int, xmlrpclib.MAXINT+1, dummy_write)
        self.assertRaises(OverflowError, m.dump_int, xmlrpclib.MININT-1, dummy_write)

    def test_dump_none(self):
        value = alist + [None]
        arg1 = (alist + [None],)
        strg = xmlrpclib.dumps(arg1, allow_none=True)
        self.assertEquals(value,
                          xmlrpclib.loads(strg)[0][0])
        self.assertRaises(TypeError, xmlrpclib.dumps, (arg1,))

    def test_dump_nodict(self):
        # try dumping an object with no __dict__ attribute
        d = object()
        self.assertRaises(TypeError, xmlrpclib.dumps, (d,))

    def test_dump_subclass(self):
        # try dumping subclass of a basic type
        class subclassInt(int):
            pass
        d = subclassInt()
        self.assertRaises(TypeError, xmlrpclib.dumps, (d,))

    def test_dump_badparam(self):
        # try dumping things that aren't a fault or tuple
        self.assertRaises(AssertionError, xmlrpclib.dumps, 'spam')
        self.assertRaises(AssertionError, xmlrpclib.dumps, 1)
        self.assertRaises(AssertionError, xmlrpclib.dumps, object())

    def test_default_encoding_issues(self):
        # SF bug #1115989: wrong decoding in '_stringify'
        utf8 = """<?xml version='1.0' encoding='iso-8859-1'?>
                  <params>
                    <param><value>
                      <string>abc \x95</string>
                      </value></param>
                    <param><value>
                      <struct>
                        <member>
                          <name>def \x96</name>
                          <value><string>ghi \x97</string></value>
                          </member>
                        </struct>
                      </value></param>
                  </params>
                  """

        # sys.setdefaultencoding() normally doesn't exist after site.py is
        # loaded.  reload(sys) is the way to get it back.
        old_encoding = sys.getdefaultencoding()
        setdefaultencoding_existed = hasattr(sys, "setdefaultencoding")
        reload(sys) # ugh!
        sys.setdefaultencoding("iso-8859-1")
        try:
            (s, d), m = xmlrpclib.loads(utf8)
        finally:
            sys.setdefaultencoding(old_encoding)
            if not setdefaultencoding_existed:
                del sys.setdefaultencoding

        items = d.items()
        if have_unicode:
            self.assertEquals(s, u"abc \x95")
            self.assert_(isinstance(s, unicode))
            self.assertEquals(items, [(u"def \x96", u"ghi \x97")])
            self.assert_(isinstance(items[0][0], unicode))
            self.assert_(isinstance(items[0][1], unicode))
        else:
            self.assertEquals(s, "abc \xc2\x95")
            self.assertEquals(items, [("def \xc2\x96", "ghi \xc2\x97")])


class HelperTestCase(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(xmlrpclib.escape("a&b"), "a&amp;b")
        self.assertEqual(xmlrpclib.escape("a<b"), "a&lt;b")
        self.assertEqual(xmlrpclib.escape("a>b"), "a&gt;b")

class FaultTestCase(unittest.TestCase):
    def test_repr(self):
        f = xmlrpclib.Fault(42, 'Test Fault')
        self.assertEqual(repr(f), "<Fault 42: 'Test Fault'>")
        self.assertEqual(repr(f), str(f))

    def test_dump_fault(self):
        f = xmlrpclib.Fault(42, 'Test Fault')
        s = xmlrpclib.dumps((f,))
        (newf,), m = xmlrpclib.loads(s)
        self.assertEquals(newf, {'faultCode': 42, 'faultString': 'Test Fault'})
        self.assertEquals(m, None)

        s = xmlrpclib.Marshaller().dumps(f)
        self.assertRaises(xmlrpclib.Fault, xmlrpclib.loads, s)


class DateTimeTestCase(unittest.TestCase):
    def test_default(self):
        t = xmlrpclib.DateTime()

    def test_time(self):
        d = 1181399930.036952
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t), '20070609T10:38:50')

    def test_time_tuple(self):
        d = (2007,6,9,10,38,50,5,160,0)
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t), '20070609T10:38:50')

    def test_time_struct(self):
        d = time.localtime(1181399930.036952)
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t), '20070609T10:38:50')

    def test_datetime_datetime(self):
        d = datetime.datetime(2007,1,2,3,4,5)
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t), '20070102T03:04:05')

    def test_datetime_date(self):
        d = datetime.date(2007,9,8)
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t), '20070908T00:00:00')

    def test_datetime_time(self):
        d = datetime.time(13,17,19)
        # allow for date rollover by checking today's or tomorrow's dates
        dd1 = datetime.datetime.now().date()
        dd2 = dd1 + datetime.timedelta(days=1)
        vals = (dd1.strftime('%Y%m%dT13:17:19'),
                dd2.strftime('%Y%m%dT13:17:19'))
        t = xmlrpclib.DateTime(d)
        self.assertEqual(str(t) in vals, True)

    def test_repr(self):
        d = datetime.datetime(2007,1,2,3,4,5)
        t = xmlrpclib.DateTime(d)
        val ="<DateTime '20070102T03:04:05' at %x>" % id(t)
        self.assertEqual(repr(t), val)

    def test_decode(self):
        d = ' 20070908T07:11:13  '
        t1 = xmlrpclib.DateTime()
        t1.decode(d)
        tref = xmlrpclib.DateTime(datetime.datetime(2007,9,8,7,11,13))
        self.assertEqual(t1, tref)

        t2 = xmlrpclib._datetime(d)
        self.assertEqual(t1, tref)

class BinaryTestCase(unittest.TestCase):
    def test_default(self):
        t = xmlrpclib.Binary()
        self.assertEqual(str(t), '')

    def test_string(self):
        d = '\x01\x02\x03abc123\xff\xfe'
        t = xmlrpclib.Binary(d)
        self.assertEqual(str(t), d)

    def test_decode(self):
        d = '\x01\x02\x03abc123\xff\xfe'
        de = base64.encodestring(d)
        t1 = xmlrpclib.Binary()
        t1.decode(de)
        self.assertEqual(str(t1), d)

        t2 = xmlrpclib._binary(de)
        self.assertEqual(str(t2), d)


class SlowParserTestCase(unittest.TestCase):
    def test_basic(self):
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)

    def test_parse(self):
        d = "I don't like spam!"
        dm = xmlrpclib.Marshaller().dumps([d])
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed[0], d)

    def test_getparser(self):
        d = "I don't like spam!"
        dm = xmlrpclib.Marshaller().dumps([d])
        p,u = xmlrpclib.getparser()
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed[0], d)

class UnmarshallerTestCase(unittest.TestCase):
    def test_badresponse(self):
        #XXX: should add some tests for _marks not being empty
        u = xmlrpclib.Unmarshaller()
        self.assertRaises(xmlrpclib.ResponseError, u.close)

    def test_bool(self):
        dm = '<params>\n<param>\n<value><boolean>0</boolean> \
                </value>\n</param>\n</params>\n'
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed, (False,))

    def test_badbool(self):
        dm = '<params>\n<param>\n<value><boolean>3</boolean> \
                </value>\n</param>\n</params>\n'
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        self.assertRaises(TypeError, p.feed, dm)

    def test_int(self):
        dm = '<params>\n<param>\n<value><int>42</int> \
                </value>\n</param>\n</params>\n'
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed, (42,))

        dm = '<params>\n<param>\n<value><i4>17</i4> \
                </value>\n</param>\n</params>\n'
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed, (17,))

    def test_emptyval(self):
        dm = '<params>\n<param>\n<value></value>\n</param>\n</params>\n'
        u = xmlrpclib.Unmarshaller()
        p = xmlrpclib.SlowParser(u)
        p.feed(dm)
        p.close()
        parsed = u.close()
        self.assertEqual(parsed, ('',))

def server(evt):
    serv = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", 8000),
                    logRequests=False, bind_and_activate=False)
    serv.socket.settimeout(3)
    serv.server_bind()
    serv.server_activate()
    serv.register_introspection_functions()
    serv.register_multicall_functions()
    serv.register_function(pow)
    serv.register_function(lambda x,y: x+y, 'add')

    class TestFunc1:
        def div(self, x, y):
            '''This is the div function'''
            return x // y

    class TestFunc2:
        def mult(self, x, y):
            '''This is the div function'''
            return x * y

        def _methodHelp(method_name):
            if method_name == 'mult':
                return 'This is the mult function'
            return 'No such method %r' % method_name


    serv.register_instance(TestFunc1())

    try:
        serv.handle_request()
    except socket.timeout:
        pass
    finally:
        serv.socket.close()
        evt.set()

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.evt = threading.Event()
        threading.Thread(target=server, args=(self.evt,)).start()
        time.sleep(.1)

    def tearDown(self):
        self.evt.wait()

    def test_baduri(self):
        # protocols other than http/https should fail
        self.assertRaises(IOError, xmlrpclib.ServerProxy, 'bogus://localhost:8000')

    def test_simple(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        self.assertEqual(p.pow(6,8), 6**8)

    def test_repr(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        prep = "<ServerProxy for localhost:8000/RPC2>"
        self.assertEqual(repr(p), prep)

    def test_missing(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        self.assertRaises(xmlrpclib.Fault, p.nonexistent_function, 42)

    def test_methodHelp(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        self.assertEqual(p.system.methodHelp('div'),
                        'This is the div function')

    def test_signatures(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        self.assertEqual(p.system.methodSignature('add'),
                        'signatures not supported')

    def test_multicall(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        multi = xmlrpclib.MultiCall(p)
        self.assertEqual(repr(multi), "<MultiCall at %x>" % id(multi))
        multi.pow(3,4)
        multi.pow(5,6)
        results = [r for r in multi()]
        self.assertEqual(results, [3**4, 5**6])

    def test_failing_multicall(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        multi = xmlrpclib.MultiCall(p)
        multi.pow(3,4)
        multi.nonexistent_method(42)
        self.assertRaises(xmlrpclib.Fault, list, multi())

    def test_introspection(self):
        p = xmlrpclib.ServerProxy('http://localhost:8000')
        expect_meths = set(['pow', 'add', 'div',
                        'system.listMethods',
                        'system.methodHelp',
                        'system.methodSignature',
                        'system.multicall'])
        self.assertEqual(set(p.system.listMethods()), expect_meths)


def test_main():
    test_support.run_unittest(XMLRPCTestCase, HelperTestCase,
            DateTimeTestCase, BinaryTestCase, SlowParserTestCase,
            FaultTestCase, ServerTestCase, UnmarshallerTestCase)


if __name__ == "__main__":
    test_main()

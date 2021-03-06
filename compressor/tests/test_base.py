from __future__ import with_statement
import os
import re

from BeautifulSoup import BeautifulSoup

from django.core.cache.backends import locmem
from django.test import TestCase

from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor


def css_tag(href, **kwargs):
    rendered_attrs = ''.join(['%s="%s" ' % (k, v) for k, v in kwargs.items()])
    template = u'<link rel="stylesheet" href="%s" type="text/css" %s/>'
    return template % (href, rendered_attrs)


test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class CompressorTestCase(TestCase):

    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = {}
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """\
<link rel="stylesheet" href="/media/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/media/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor(self.css)

        self.js = """\
<script src="/media/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor(self.js)

    def test_css_split(self):
        out = [
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css', u'one.css'), u'css/one.css', u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" />'),
            (SOURCE_HUNK, u'p { border:5px solid green;}', None, u'<style type="text/css">p { border:5px solid green;}</style>'),
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'css', u'two.css'), u'css/two.css', u'<link rel="stylesheet" href="/media/css/two.css" type="text/css" />'),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], x[2], self.css_node.parser.elem_str(x[3][0])) for x in split]
        self.assertEqual(out, split)

    def test_css_hunks(self):
        out = ['body { background:#990; }', u'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, list(self.css_node.hunks()))

    def test_css_output(self):
        out = u'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        hunks = '\n'.join([h for h in self.css_node.hunks()])
        self.assertEqual(out, hunks)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}[\.\d]+$')
        for date in self.css_node.mtimes:
            self.assertTrue(is_date.match(str(float(date))),
                "mtimes is returning something that doesn't look like a date: %s" % date)

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        self.assertEqual(self.css, self.css_node.output())

    def test_cachekey(self):
        is_cachekey = re.compile(r'\w{12}')
        self.assertTrue(is_cachekey.match(self.css_node.cachekey),
            "cachekey is returning something that doesn't look like r'\w{12}'")

    def test_css_return_if_on(self):
        output = css_tag('/media/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_split(self):
        out = [
            (SOURCE_FILE, os.path.join(settings.COMPRESS_ROOT, u'js', u'one.js'), u'js/one.js', '<script src="/media/js/one.js" type="text/javascript"></script>'),
            (SOURCE_HUNK, u'obj.value = "value";', None, '<script type="text/javascript">obj.value = "value";</script>'),
        ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], x[2], self.js_node.parser.elem_str(x[3][0])) for x in split]
        self.assertEqual(out, split)

    def test_js_hunks(self):
        out = ['obj = {};', u'obj.value = "value";']
        self.assertEqual(out, list(self.js_node.hunks()))

    def test_js_output(self):
        out = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_js_override_url(self):
        self.js_node.context.update({'url': u'This is not a url, just a text'})
        out = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_css_override_url(self):
        self.css_node.context.update({'url': u'This is not a url, just a text'})
        output = css_tag('/media/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_return_if_off(self):
        try:
            enabled = settings.COMPRESS_ENABLED
            precompilers = settings.COMPRESS_PRECOMPILERS
            settings.COMPRESS_ENABLED = False
            settings.COMPRESS_PRECOMPILERS = {}
            self.assertEqual(self.js, self.js_node.output())
        finally:
            settings.COMPRESS_ENABLED = enabled
            settings.COMPRESS_PRECOMPILERS = precompilers

    def test_js_return_if_on(self):
        output = u'<script type="text/javascript" src="/media/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(output, self.js_node.output())

    def test_custom_output_dir(self):
        try:
            old_output_dir = settings.COMPRESS_OUTPUT_DIR
            settings.COMPRESS_OUTPUT_DIR = 'custom'
            output = u'<script type="text/javascript" src="/media/custom/js/066cd253eada.js"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = ''
            output = u'<script type="text/javascript" src="/media/js/066cd253eada.js"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
            settings.COMPRESS_OUTPUT_DIR = '/custom/nested/'
            output = u'<script type="text/javascript" src="/media/custom/nested/js/066cd253eada.js"></script>'
            self.assertEqual(output, JsCompressor(self.js).output())
        finally:
            settings.COMPRESS_OUTPUT_DIR = old_output_dir


def make_elems_str(parser, elems):
    return "".join([parser.elem_str(x) for x in elems])


class CompressorGroupFirstTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = {}
        self.css = """\
<link rel="stylesheet" href="/media/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/media/css/one.less" type="text/less" />
<link rel="stylesheet" href="/media/css/two.less" type="text/less" />"""
        self.css_node = CssCompressor(self.css)
        self.css_node.opts = {'group_first': 'true'}

        self.js = """\
<script src="/media/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>
<script src="/media/js/one.coffee" type="text/coffeescript"></script>
<script src="/media/js/two.coffee" type="text/coffeescript"></script>"""
        self.js_node = JsCompressor(self.js)

    def test_css_group(self):
        out = [
            [SOURCE_HUNK,
             u'body { background:#990; }p { border:5px solid green;}',
             u'css/one.css',
             u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" /><style type="text/css">p { border:5px solid green;}</style>'],
            [SOURCE_HUNK,
             u'body { background:#990; }body { color:#fff; }',
             u'css/one.less',
             u'<link rel="stylesheet" href="/media/css/one.less" type="text/less" /><link rel="stylesheet" href="/media/css/two.less" type="text/less" />'],
        ]
        split = self.css_node.group_contents()
        split = [[x[0], x[1], x[2], make_elems_str(self.css_node.parser, x[3])] for x in split]
        self.assertEqual(out, split)

    def test_css_single(self):
        css_node = CssCompressor("""<link rel="stylesheet" href="/media/css/one.css" type="text/css" />""")
        css_node.opts = {'group_first': 'true'}
        out = [
            [SOURCE_FILE,
             os.path.join(settings.COMPRESS_ROOT, u'css', u'one.css'),
             u'css/one.css',
             u'<link rel="stylesheet" href="/media/css/one.css" type="text/css" />'],
        ]
        split = css_node.group_contents()
        split = [[x[0], x[1], x[2], make_elems_str(self.css_node.parser, x[3])] for x in split]
        self.assertEqual(out, split)

    def test_js_group(self):
        out = [
            [SOURCE_HUNK,
             u'obj = {};obj.value = "value";',
             u'js/one.js',
             '<script src="/media/js/one.js" type="text/javascript"></script><script type="text/javascript">obj.value = "value";</script>'],
            [SOURCE_HUNK,
             u'# this is a comment.\n# this is a comment.',
             u'js/one.coffee',
             '<script src="/media/js/one.coffee" type="text/coffeescript"></script><script src="/media/js/two.coffee" type="text/coffeescript"></script>'],
        ]
        split = self.js_node.group_contents()
        split = [[x[0], x[1], x[2], make_elems_str(self.js_node.parser, x[3])] for x in split]
        self.assertEqual(out, split)


class CssMediaTestCase(TestCase):
    def setUp(self):
        self.css = """\
<link rel="stylesheet" href="/media/css/one.css" type="text/css" media="screen">
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/media/css/two.css" type="text/css" media="all">
<style type="text/css">h1 { border:5px solid green;}</style>"""

    def test_css_output(self):
        css_node = CssCompressor(self.css)
        links = BeautifulSoup(css_node.output()).findAll('link')
        media = [u'screen', u'print', u'all', None]
        self.assertEqual(len(links), 4)
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_avoid_reordering_css(self):
        css = self.css + '<style type="text/css" media="print">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        media = [u'screen', u'print', u'all', None, u'print']
        links = BeautifulSoup(css_node.output()).findAll('link')
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_passthough_when_compress_disabled(self):
        original_precompilers = settings.COMPRESS_PRECOMPILERS
        settings.COMPRESS_ENABLED = False
        settings.COMPRESS_PRECOMPILERS = (
            ('text/foobar', 'python %s {infile} {outfile}' % os.path.join(test_dir, 'precompiler.py')),
        )
        css = """\
<link rel="stylesheet" href="/media/css/one.css" type="text/css" media="screen">
<link rel="stylesheet" href="/media/css/two.css" type="text/css" media="screen">
<style type="text/foobar" media="screen">h1 { border:5px solid green;}</style>"""
        css_node = CssCompressor(css)
        output = BeautifulSoup(css_node.output()).findAll(['link', 'style'])
        self.assertEqual([u'/media/css/one.css', u'/media/css/two.css', None],
                         [l.get('href', None) for l in output])
        self.assertEqual([u'screen', u'screen', u'screen'],
                         [l.get('media', None) for l in output])
        settings.COMPRESS_PRECOMPILERS = original_precompilers


class VerboseTestCase(CompressorTestCase):

    def setUp(self):
        super(VerboseTestCase, self).setUp()
        settings.COMPRESS_VERBOSE = True


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, locmem.CacheClass)

import os, sys, time
from threading import Thread
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

from docutils.core import publish_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

JS_HEADER = '''
<script type='text/javascript' src='http://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js'></script>
<script type='text/javascript'>
function pollServer(){
    console.log('pollServer');
    $.ajax({
        type: 'POST',
        url: '.',
        async: true,
        timeout: 50000,
        success: function(data) {
            window.location.reload();
        },
        error: function(req, status, err) {
            pollServer();
        }
    });
}
pollServer()
</script>
</head>
'''

class Null(object):
    def write(self, s): pass
null = Null()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer): pass

class Reloader(FileSystemEventHandler):
    def __init__(self, host, port, handler, *args, **kwargs):
        self.host = host
        self.port = port
        self.handler = handler
        super(Reloader, self).__init__(*args, **kwargs)

    def on_modified(self, event):
        RSTHandler._reload = True

    def spawn_server(self):
        self.server = ThreadingHTTPServer((self.host, self.port), self.handler)
        self._thread = Thread(target=self.server.serve_forever)
        self._thread.start()

    def stop_server(self):
        self.server.shutdown()
        self._thread.join()

class RSTHandler(BaseHTTPRequestHandler):
    _reload = False

    def log_message(self, *args): pass

    def send_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text-plain')
        self.end_headers()

    def do_GET(self):
        self.send_headers()
        with open(self.source) as src:
            _stdout, sys.stdout = sys.stdout, null
            body = publish_file(source=src, writer_name='html')
            sys.stdout = _stdout
            body = body.replace('</head>', JS_HEADER)
            self.wfile.write(body)

    def do_POST(self):
        self.send_headers()
        while True:
            if RSTHandler._reload: break
        RSTHandler._reload = False

if __name__ == '__main__':
    source = sys.argv[1]
    RSTHandler.source = source
    event_handler = Reloader('', 8000, RSTHandler)
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(source))
    observer.start()
    event_handler.spawn_server()
    print 'View reStructuredText document at http://127.0.0.1:8000/'
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        event_handler.stop_server()
    observer.join()

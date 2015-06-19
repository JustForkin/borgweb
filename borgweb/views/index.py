"""
main view
"""

import os
import subprocess
import time

from flask import current_app, render_template, jsonify

from . import blueprint

process = None


@blueprint.route('/backup/start', methods=['POST'])
def backup_start():
    env = dict(current_app.config)
    now = time.time()
    utc = time.gmtime(now)
    localtime = time.localtime(now)
    env['LOCALTIME'] = time.strftime('%Y-%m-%d-%H:%M:%S', localtime)
    env['UTC'] = time.strftime('%Y-%m-%d-%H:%M:%S', utc)
    cmd = env['BACKUP_CMD'].format(**env)
    global process
    if process is None or process.returncode is not None:
        # no process ever run or process has terminated
        process = subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None)
        msg = "started, pid=%d" % process.pid
    else:
        msg = "already running"
    return jsonify(dict(msg=msg, pid=process.pid))


@blueprint.route('/backup/status')
def backup_rc():
    global process
    if process is not None:
        rc = process.poll()
        if rc is None:
            msg = 'running'
        else:
            msg = 'not running, last rc=%d' % rc
    else:
        msg = 'not running'
        rc = -1
    return jsonify(dict(msg=msg, rc=rc))


@blueprint.route('/backup/stop', methods=['POST'])
def backup_stop():
    global process
    if process is None:
        rc = -1
        msg = 'not running'
    else:
        try:
            process.terminate()
            for t in range(10):
                rc = process.poll()
                if rc is not None:
                    msg = 'terminated'
                    break  # process has terminated
                time.sleep(1)
            else:
                process.kill()
                msg = 'killed'
                rc = -1
        except ProcessLookupError:
            rc = -1
            msg = 'not running'
    return jsonify(dict(msg=msg, rc=rc))


def _get_logs():
    log_dir = current_app.config['LOG_DIR']
    log_dir = os.path.abspath(log_dir)
    try:
        log_files = os.listdir(log_dir)
    except OSError:
        log_files = []
    return log_dir, sorted(log_files, reverse=True)


def _get_log_lines(log_dir, log_file, offset, linecount=None):
    log_file = os.path.join(log_dir, log_file)
    with open(log_file, 'r') as f:
        f.seek(offset)
        if linecount is None:
            log_lines = f.readlines()
        else:
            log_lines = []
            for i in range(linecount):
                line = f.readline()
                if not line:
                    break
                log_lines.append(line)
        log_lines = [line.rstrip('\n') for line in log_lines]
        offset = f.tell()
    return log_file, offset, log_lines


@blueprint.route('/logs/<int:index>/<offset>:<linecount>')
def get_log_fragment(index, offset, linecount):
    try:
        offset = int(offset)
    except ValueError:
        offset = 0
    try:
        linecount = int(linecount)
    except ValueError:
        linecount = None
    log_dir, log_files = _get_logs()
    try:
        log_file = log_files[index]
    except IndexError:
        log_file = ''
    if log_file:
        log_file, offset, log_lines = _get_log_lines(log_dir, log_file, offset, linecount)
    else:
        log_lines = []
    return jsonify(dict(fname=log_file, lines=log_lines, offset=offset))


@blueprint.route('/logs/<int:index>')
def get_log(index):
    log_dir, log_files = _get_logs()
    try:
        log_file = log_files[index]
    except IndexError:
        log_file = ''
    else:
        log_file = os.path.join(log_dir, log_file)
    return jsonify(dict(log_file=log_file))


@blueprint.route('/logs')
def get_logs():
    log_dir, log_files = _get_logs()
    return jsonify(dict(log_dir=log_dir,
                        log_files=list(enumerate(log_files))))


@blueprint.route('/')
def index():
    return render_template('index.html')

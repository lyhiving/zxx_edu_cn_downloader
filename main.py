from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from seleniumwire.utils import decode
import math
from urllib.parse import urljoin, urlsplit
import json
import requests
from pathlib import Path
from PyPDF2 import PdfReader
from loguru import logger
import sys
import subprocess
import cv2 as cv
import pytesseract as ocr
import re
from pip._vendor.rich.progress import Progress
from datetime import datetime as dt


logger.remove()
logger.add(sys.stdout, level="WARNING")
logger = logger.opt(colors=True)

cwd = Path(__file__).parents[0]
resources_dir = Path(cwd, 'resources')
downloads_dir = Path(cwd, 'downloads')
downloads_dir.mkdir(exist_ok=True)

def save_file(resource, save_dir):
    '''基于文件类型，保存文件
    '''
    resource_type = resource['resource_type']

    file_name = save_dir.parts[-1][3:]
    if resource_type == 'video':
        video_extend = resource['video_extend']

        file_name += '_视频课程.mp4'
        file_path = Path(save_dir, file_name)
        duration = sorted(video_extend['files'], key=lambda url: url['quality'])[-1]['duration']
        if not file_path.exists() or not check_video_duration(file_path, duration, False):
            url = sorted(video_extend['urls'], key=lambda url: url['quality'])[-1]['urls'][0]
            ffmpeg_download(url, file_path)
        check_video_duration(file_path, duration)
        # check_video_title(file_path)
            
    elif resource_type == 'document':
        document_extend = resource['document_extend']

        title = document_extend['title']
        file_name += f'_{title}.pdf'
        file_path = Path(save_dir, file_name)
        
        if not file_path.exists():
            host = document_extend['hosts'][0]
            for file in document_extend['files']:
                if file['type'] == 'pdf':
                    url = file['file_urls'][0]
                    with open(file_path, 'wb') as f:
                        f.write(requests.get(urljoin(host, url)).content)
        
        # check_pdf_title(file_path)
    logger.debug(f'finished write: {file_name}!')

def check_video_duration(file_path, duration, log=True):
    '''视频长度验证

    file_path:  视频文件Path
    duration:   resources.json中定义的duration
    log:        是否输出log
    '''
    try:
        app = subprocess.Popen(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"', stdout=subprocess.PIPE, encoding='utf8')
        video_duration = math.floor(float(app.stdout.read().strip()))
    except:
        video_duration = 0
    try:
        assert abs(video_duration - duration) <= 3
    except:
        if log:
            logger.warning(f'{file_path.parts[-1]} <r>video_duration</>: {video_duration} == {duration}')
        return False
    return True

def check_video_title(file_path):
    '''视频标题验证

    file_path:  视频文件Path
    '''
    cap = cv.VideoCapture(str(file_path))

    fps = cap.get(cv.CAP_PROP_FPS)
    cap.set(cv.CAP_PROP_POS_FRAMES, fps * 6)
    _, frame = cap.read()

    scaned_text = ocr.image_to_string(frame, lang='chi_sim', config='--psm 11')
    cap.release()

    # 定位第二行文字
    title = re.split('\n+', scaned_text)[1]
    # 去掉括号和括号里面的内容。因为这部分很难识别，并且作者也不规范
    title = re.compile('\(.*\)').sub('', title)
    title = title.replace(' ', '')

    try:
        assert file_path.parts[-2][3:].find(title) != -1
    except:
        logger.warning(f'{file_path.parts[-1]} <g>video_title</>: {title} == {file_path.parts[-2][3:]}')

def check_pdf_title(file_path):
    '''文档标题验证
    
    file_path:  视频文件Path
    '''
    reader = PdfReader(file_path)
    for page in reader.pages:
        for line in page.extract_text().split('\n'):
            if line.find('课题') != -1:
                pdf_course_title = line.split('课题')[-1].replace(' ', '')
                course_title = file_path.parts[-2][3:]
                try:
                    assert course_title.find(pdf_course_title) != -1
                    return
                except:
                    logger.warning(f'{file_path.parts[-1]} <e>pdf_title</>: {pdf_course_title} == {course_title}')

def get_web_data(url):
    '''下载fulls.json，获取resources.json的request.url
    '''
    options = {
        'request_storage': 'memory'
    }
    driver = webdriver.Chrome(seleniumwire_options=options)
    driver.get(url)
    try:
        WebDriverWait(driver, 5).until(lambda x: x.find_element(By.CLASS_NAME, "course-catalog-inner"))
    except:
        raise LookupError('找不到需要的页面元素')

    results = {}

    for request in driver.requests:
        response = request.response
        if response:
            if request.url.find('fulls.json') != -1:
                body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
                fulls_data = json.loads(body.decode())
                
                results['fulls'] = fulls_data
            elif request.url.find('resources.json') != -1:
                results['resources'] = request.url
    
    if results == {}:
        raise ValueError('找不到fulls.json或者resources.json')
    
    return results

def run(url):
    '''入口
    
    url: 课程地址。格式为：`https://www.zxx.edu.cn/syncClassroom/classActivity?activityId=*`
    '''
    # with open(Path(resources_dir, 'fulls.json'), encoding='utf8') as f:
    #     fulls_data = json.load(f)
    
    web_data = get_web_data(url)
    fulls_data = web_data['fulls']
    resources_url = web_data['resources']
    splited = urlsplit(resources_url).path.split('/')
    
    activity_set_name = fulls_data['activity_set_name'].strip()
    parent_path = Path(downloads_dir, activity_set_name)
    parent_path.mkdir(exist_ok=True)

    for node in fulls_data['nodes']:
        node_path = Path(parent_path, node['node_name'].strip())
        node_path.mkdir(exist_ok=True)

        for child in node['child_nodes']:
            child_path = Path(node_path, f"{child['order_no']:02} {child['node_name'].strip()}")
            child_path.mkdir(exist_ok=True)
            
            node_id = child['node_id']
            url = f'https://s-file-1.ykt.cbern.com.cn/zxx/s_course/v1/x_class_hour_activity/{node_id}/resources.json'
            
            splited[-2] = node_id
            url = urljoin(resources_url, '/'.join(splited))

            resources_data = requests.get(url).json()
            for resource in resources_data:
                save_file(resource, child_path)

def test_re():
    str = '国 家 中 小 学 课 程 资 源\n\n中 学 序 曲 ( 第 = 谅 )\n\n年 _ 级 : 七年 级 “ 学 _ 科 : 道 德 与 法 治 ( 统 编 版 )\n主 讲 人 : 陈 华 “ 学 _ 校 : 清 华 大 学 附 属 中 学 上 地 学 校\n\n二 人 一 - 一 理\n\x0c'
    title = re.split('\n+', str)[1]
    title = re.compile('\(.*\)').sub('', title)
    title = title.replace(' ', '')

def ffmpeg_download(url, file_path):
    '''使用ffmpeg下载m3u8

    url:        m3u8文件url
    file_path:  视频文件Path
    '''
    # url = r'https://r1-ndr.ykt.cbern.com.cn/edu_product/65/video/17b5f9b1547a11eb96b8fa20200c3759/c0aa65c73e5d2ce09fc31efa9aba926d.640.360.false/c0aa65c73e5d2ce09fc31efa9aba926d.640.360.m3u8'
    # file_path = Path(downloads_dir, 'test_progress.mp4')
    app = subprocess.Popen(f'ffmpeg -i {url} -progress pipe:2 -c copy "{file_path}" -y',
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, encoding='utf8')
    
    file_name = file_path.parts[-1]
    
    duration_pattern = re.compile('Duration:(.*?),')
    out_time_pattern = re.compile('out_time=(.*)')

    with Progress() as progress:
        task = None
        for line in app.stderr:
            if task is None:
                duration_pattern_matched = duration_pattern.search(line)
                if duration_pattern_matched:
                    duration_str = duration_pattern_matched.group(1).strip()
                    duration_delta = dt.strptime(duration_str, '%H:%M:%S.%f') - dt(1900, 1, 1)
                    duration = duration_delta.total_seconds()
                    task = progress.add_task(f'[magenta]downloading: {file_name}', total=duration)
            else:
                out_time_pattern_matched = out_time_pattern.search(line)
                if out_time_pattern_matched:
                    out_time_str = out_time_pattern_matched.group(1).strip()
                    out_time_delta = dt.strptime(out_time_str, '%H:%M:%S.%f') - dt(1900, 1, 1)
                    out_time = out_time_delta.total_seconds()
                    out_time = math.ceil(out_time_delta.total_seconds())
                    progress.update(task, completed=out_time)

if __name__ == '__main__':
    # url = r'https://www.zxx.edu.cn/syncClassroom/classActivity?activityId=df057863-c92d-4b62-bbb1-d1dfcd85c5d2'
    try:
        url = sys.argv[1]
        run(url)
    except IndexError:
        logger.error('缺少url')
    except Exception as e:
        logger.error(e)
    
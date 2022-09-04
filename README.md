# 国家中小学智慧教育平台-资源下载

```powershell
# 需要配置selenium
# progress需要22版本以上的pip
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# url:  课程地址。格式为：`https://www.zxx.edu.cn/syncClassroom/classActivity?activityId=*`
python main.py url
```

1. 默认只有对于视频时长的验证，确保下载完成

额外的对于视频标题和pdf标题的验证，需要依据实际情况去写


## 这是一个动态加载的网站
直接找`api`好了

1. 核心是`fulls.json`
数据实际上是伪动态的

https://www.zxx.edu.cn/syncClassroom/classActivity?activityId=ad610237-db27-4d86-8105-f7262c2e3fdf

https://s-file-1.ykt.cbern.com.cn/zxx/s_course/v2/activity_sets/3f9ced7c-f6d7-4e86-b325-38ac946afc1b/fulls.json

https://s-file-1.ykt.cbern.com.cn/zxx/s_course/v1/x_class_hour_activity/ad610237-db27-4d86-8105-f7262c2e3fdf/resources.json

https://s-file-1.ykt.cbern.com.cn/zxx/s_course/v1/x_class_hour_activity/ad610237-db27-4d86-8105-f7262c2e3fdf/lecturers.json

2. `m3u8` & video

https://r3-ndr.ykt.cbern.com.cn/edu_product/65/video/17b68a16547a11eb96b8fa20200c3759/99bfa99daaa10801443529f52fe08db7.1280.720.false/99bfa99daaa10801443529f52fe08db7.1280.720.m3u8

https://r1-ndr.ykt.cbern.com.cn/edu_product/65/video/17b68a16547a11eb96b8fa20200c3759/99bfa99daaa10801443529f52fe08db7.1280.720.false/99bfa99daaa10801443529f52fe08db7.1280.720-00003.ts

- `m3u8_To_MP4`居然是有bug的，默认会少掉开头的一小段
其实本来就应该做验证，毕竟是下载，而且`resources`中就有`duration`

- 视频下载
可以直接用`ffmpeg`指令来下载m3u8的内容
`ffmpeg -i '*.m3u8' -c copy test.mp4`

3. `pdf`

https://r1-ndr.ykt.cbern.com.cn/edu_product/65/document/1bc74fe7547a11eb96b8fa20200c3759/pdf.pdf
/edu_product/65/document/1bc74fe7547a11eb96b8fa20200c3759/pdf.pdf


## 数据验证

虽然感觉不可能会出错，但是毕竟是离线使用的，还是验证一下好了

1. pdf
- 文档标题验证
直接定位`课题`拿到标题，然后匹配

- 存在一些命名不规范、识别错误、
这部分就直接人工验证了

2. mp4
- 视频长度验证
`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4`

- 视频标题验证
以视频开头的5秒处的封面进行图像识别
从顺序来说，标题肯定是在第二行的

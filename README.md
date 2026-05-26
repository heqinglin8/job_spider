# job_spider
job_spider
# 使用方法
  pip3 install requests
  ## 抓取广州所有职位（含详情，最多 1000 条）
  python3 gd_job_spider.py --cities 广州
  ## 多城市 + 关键词，跳过详情（更快）
  python3 gd_job_spider.py --cities 广州 深圳 --keyword 工程师 --no-detail
  ## 快速测试（只抓 3 页）
  python3 gd_job_spider.py --cities 广州 --max-pages 3
  ## 抓取全省所有城市，保存到指定目录
  python3 gd_job_spider.py --all-cities --output-dir ./output

你是一个专业的爬虫工程师，请分析这个地址和访问这个地址获取到的内容：https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/#/search?type=1&fromSSO=1，然后写一个爬虫脚本，这个脚本满足：
1.能抓取到设置的城市的所有职位，这职位有详情url的话，访问详情，然后抓取
2.这个职位包含职位title，标签信息，其他福利，联系电话，岗位描述，学历要求，工作经验，工作地点

# 图片水印脚本
安装依赖：

```bash
pip3 install pillow
```

Windows 也可以这样安装：

```bash
python -m pip install pillow
```

给图片底部 40px 处加一行红色醒目水印：

```bash
python3 image_watermark.py images/group-qr-code.png
```

Windows 命令示例：

```bash
python image_watermark.py images\group-qr-code.png
```

自定义水印文案和输出路径：

```bash
python3 image_watermark.py images/group-qr-code.png \
  --text "点击本图->长按加群！" \
  --output images/group-qr-code-watermarked.png
```

Windows 自定义输出示例：

```bash
python image_watermark.py images\group-qr-code.png ^
  --text "点击本图->长按加群！" ^
  --output images\group-qr-code-watermarked.png
```

说明：
1. 默认文案写在脚本常量 `DEFAULT_WATERMARK_TEXT`，也可以通过 `--text` 覆盖。
2. 水印文字会以 **红色加粗** 方式渲染；优先使用系统粗体中文字体，必要时会额外做加粗增强。
3. 文字会在图片宽度允许的前提下自动放大；如果文案太长，会自动缩小以适配宽度。
4. 脚本会优先保证清晰度，并尽量把输出图片控制到 **不大于原图**；如果做不到，也会控制在 **原图 120% 以内**。
5. 脚本已兼容 **macOS / Windows**，会优先自动查找系统里的常见中文字体；如果本机缺少可用字体，可以通过 `--font` 显式指定字体文件。

# job_spider
job_spider
# 使用方法
  pip3 install requests
  ## 抓取广州所有职位（含详情，最多 1000 条），结果默认保存到 output/
  python3 gd_job_spider.py --cities 广州
  ## 多城市 + 关键词，跳过详情（更快）
  python3 gd_job_spider.py --cities 广州 深圳 --keyword 工程师 --no-detail
  ## 快速测试（只抓 3 页）
  python3 gd_job_spider.py --cities 广州 --max-pages 3
  ## 抓取全省所有城市，结果默认保存到 output/
  python3 gd_job_spider.py --all-cities

  ## 也可以显式指定输出目录
  python3 gd_job_spider.py --all-cities --output-dir ./output

## 登录 token 配置

脚本会优先读取环境变量 `GD_JOB_TOKEN`，其次读取项目根目录的 `.gd_job_token` 文件。文件中只需放一行 token，也可以包含 `Bearer ` 前缀：

```bash
printf '%s\n' '你的token' > .gd_job_token
python3 gd_job_spider.py --cities 广州
```

如果本地 token 缺失或已过期，脚本会自动回退到浏览器登录。扫码登录成功后，终端会打印 token 和 Cookie，方便复制使用；新 token 也会自动缓存到 `.gd_job_token`。也可以通过 `--token-file` 指定其他缓存文件。

## Cookie 配置

如果需要手工配置 Cookie，将浏览器复制出的完整 Cookie 请求头原样放入项目根目录的 `cookie.txt` 文件（不要拆分，也不要删除 `../issoYH_MASS_TOKEN` 这类名称）：

```text
Hm_lvt_6ab51e6b7b23ac7b2893ecb75585250d=1793541645; Hm_lpvt_6ab51e6b7b23ac7b2893ecb75585250d=1793541675; Client-ID=你的值; ../issoYH_MASS_TOKEN=你的值
```

也可以通过环境变量配置：

```bash
export GD_JOB_COOKIE='完整的Cookie字符串'
python3 gd_job_spider.py --cities 广州
```

环境变量优先于 `cookie.txt`；也可以使用 `--cookie-file` 指定其他 Cookie 文件。程序也兼容读取旧版本的 `.gd_job_cookie`。Cookie 和 token 都是敏感登录凭证，请勿提交或分享。

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

图形界面启动：

1. **macOS**：双击 `launch_image_watermark.command`
2. **Windows**：双击 `launch_image_watermark.bat`
3. 也可以直接运行：

```bash
python3 image_watermark.py --gui
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
2. 直接运行 `image_watermark.py` 且不带参数时，也会自动打开 GUI。
3. GUI 中选择一张图片，可在输入框自定义水印内容；如果留空，会自动使用默认文案 `点击本图->长按加群！`。
4. 水印文字会以 **红色加粗 + 高亮黄色描边** 方式渲染；优先使用系统粗体中文字体，必要时会额外做加粗增强。
5. 文字会在图片宽度允许的前提下自动放大；如果文案太长，会自动缩小以适配宽度。
6. 脚本会优先保证清晰度；如果生成结果超过原图的 **120%**，会继续自动压缩，直到降到 **原图 120% 以内** 再输出。
7. 脚本已兼容 **macOS / Windows**，会优先自动查找系统里的常见中文字体；如果本机缺少可用字体，可以通过 `--font` 显式指定字体文件。
